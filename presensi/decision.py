"""Mesin keputusan presensi.

Dirancang modular per syarat: opsi QR dan Wi-Fi menyusul -- tambahkan
fungsi cek baru di sini dan panggil dari presensi/views.py, tanpa perlu
mengubah cara syarat lokasi/wajah bekerja.

Gerbang-DAN (lihat CLAUDE.md § 3): presensi diterima HANYA kalau cek_lokasi
DAN verifikasi_wajah dua-duanya lolos. Kalau salah satu gagal, presensi
DITOLAK (bukan cuma ditandai) dan dicatat ke LogKecurangan -- lihat
presensi/views.py untuk penggabungan gerbangnya.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from .face import SKOR_KEMIRIPAN_MINIMUM, dekripsi_embedding, ekstrak_satu_wajah, kemiripan_kosinus
from .geo import jarak_meter
from .models import EnrolmentWajah, HariLibur, KelompokPresensi, LokasiKantor, StatusPresensi

AKURASI_GPS_MAKSIMAL_M = 50


@dataclass
class HasilCekLokasi:
    lolos: bool
    alasan: Optional[str]
    lokasi: Optional[LokasiKantor]
    jarak_m: Optional[float]


def cek_lokasi(lat, lng, akurasi_m) -> HasilCekLokasi:
    """Syarat 1: titik GPS harus di dalam radius geofence salah satu
    LokasiKantor aktif, dengan akurasi GPS yang cukup baik (akurasi buruk
    adalah indikasi umum mock-location)."""
    if akurasi_m is None or akurasi_m > AKURASI_GPS_MAKSIMAL_M:
        return HasilCekLokasi(False, "akurasi_buruk", None, None)

    lokasi_terpilih = None
    jarak_terdekat = None
    for lokasi in LokasiKantor.objects.filter(aktif=True):
        jarak = jarak_meter(lat, lng, lokasi.latitude, lokasi.longitude)
        if jarak <= lokasi.radius_meter and (jarak_terdekat is None or jarak < jarak_terdekat):
            lokasi_terpilih = lokasi
            jarak_terdekat = jarak

    if lokasi_terpilih is None:
        return HasilCekLokasi(False, "di_luar_radius", None, None)

    return HasilCekLokasi(True, None, lokasi_terpilih, jarak_terdekat)


def resolve_kelompok(user) -> Optional[KelompokPresensi]:
    """Kelompok presensi yang berlaku untuk user, ditentukan OTOMATIS dari
    role akun (lihat KelompokPresensi.roles). None kalau role user belum
    dipetakan ke kelompok mana pun -- presensi tetap jalan, jam kerja
    LokasiKantor dipakai sebagai fallback (lihat tentukan_status_waktu)."""
    return (
        KelompokPresensi.objects.filter(aktif=True, roles__contains=[user.role])
        .order_by("id")
        .first()
    )


def is_hari_libur(tanggal) -> bool:
    return HariLibur.objects.filter(tanggal=tanggal).exists()


def _hari_kerja_normal(kelompok, tanggal) -> bool:
    """True kalau tanggal adalah hari kerja biasa -- bukan hari libur
    ataupun hari di luar hari_kerja kelompok (mis. Minggu). Dipakai
    bersama oleh tentukan_status_waktu & hitung_ketepatan_masuk/pulang
    supaya konsisten (lihat CLAUDE.md § 9)."""
    if tanggal is None:
        return True
    if is_hari_libur(tanggal):
        return False
    if kelompok is not None and tanggal.weekday() not in kelompok.hari_kerja:
        return False
    return True


def _selisih_menit(jam_jadwal, jam_aktual) -> int:
    """Selisih jam_aktual terhadap jam_jadwal dalam menit -- positif kalau
    jam_aktual lebih lambat dari jadwal, negatif kalau lebih awal."""
    return (jam_aktual.hour * 60 + jam_aktual.minute) - (jam_jadwal.hour * 60 + jam_jadwal.minute)


def tentukan_status_waktu(lokasi: LokasiKantor, jam_saat_ini, kelompok=None, tanggal=None) -> str:
    """hadir vs telat. Jam kerja dari KelompokPresensi (kalau resolve utk
    role user) diprioritaskan di atas jam_masuk/toleransi_menit LokasiKantor
    -- fallback ke lokasi berlaku kalau role belum dipetakan ke kelompok
    mana pun. Hari libur atau hari non-kerja kelompok (mis. Minggu) selalu
    HADIR tanpa hitungan telat -- lihat CLAUDE.md § 9."""
    if not _hari_kerja_normal(kelompok, tanggal):
        return StatusPresensi.HADIR

    jam_masuk = kelompok.jam_masuk if kelompok is not None else lokasi.jam_masuk
    toleransi_menit = kelompok.toleransi_menit if kelompok is not None else lokasi.toleransi_menit

    batas_telat = (
        datetime.combine(datetime.min, jam_masuk) + timedelta(minutes=toleransi_menit)
    ).time()
    return StatusPresensi.TELAT if jam_saat_ini > batas_telat else StatusPresensi.HADIR


def hitung_ketepatan_masuk(lokasi: LokasiKantor, jam_aktual, kelompok=None, tanggal=None):
    """(menit_lebih_awal, menit_terlambat) saat absen masuk -- selisih
    MURNI dari jam_masuk jadwal (kelompok/lokasi), TIDAK memperhitungkan
    toleransi_menit (toleransi cuma dipakai untuk status HADIR/TELAT di
    tentukan_status_waktu). 0/0 di hari libur atau hari non-kerja
    kelompok, konsisten dengan tentukan_status_waktu."""
    if not _hari_kerja_normal(kelompok, tanggal):
        return 0, 0

    jam_masuk = kelompok.jam_masuk if kelompok is not None else lokasi.jam_masuk
    selisih = _selisih_menit(jam_masuk, jam_aktual)
    return (0, selisih) if selisih > 0 else (-selisih, 0)


def hitung_ketepatan_pulang(lokasi: LokasiKantor, jam_aktual, kelompok=None, tanggal=None):
    """(menit_pulang_cepat, menit_lembur) saat absen pulang -- selisih
    dari jam_pulang jadwal (kelompok/lokasi). 0/0 di hari libur atau hari
    non-kerja kelompok, konsisten dengan tentukan_status_waktu."""
    if not _hari_kerja_normal(kelompok, tanggal):
        return 0, 0

    jam_pulang = kelompok.jam_pulang if kelompok is not None else lokasi.jam_pulang
    selisih = _selisih_menit(jam_pulang, jam_aktual)
    return (0, selisih) if selisih > 0 else (-selisih, 0)


@dataclass
class HasilCekWajah:
    lolos: bool
    alasan: Optional[str]
    skor_kemiripan: Optional[float]


def verifikasi_wajah(user, berkas_selfie) -> HasilCekWajah:
    """Syarat 2: selfie saat absen harus cocok dengan embedding hasil
    enrolment (presensi/face.py) DAN lolos pemeriksaan liveness dasar."""
    enrolment = EnrolmentWajah.objects.filter(user=user, consent_disetujui=True).first()
    if enrolment is None:
        return HasilCekWajah(False, "belum_enrolment_wajah", None)

    wajah, alasan = ekstrak_satu_wajah(berkas_selfie)
    if wajah is None:
        return HasilCekWajah(False, alasan, None)

    embedding_tersimpan = dekripsi_embedding(bytes(enrolment.embedding_terenkripsi))
    skor = kemiripan_kosinus(embedding_tersimpan, wajah.embedding)

    if skor < SKOR_KEMIRIPAN_MINIMUM:
        return HasilCekWajah(False, "wajah_tidak_cocok", skor)

    return HasilCekWajah(True, None, skor)
