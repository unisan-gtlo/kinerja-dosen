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
from .models import EnrolmentWajah, LokasiKantor, StatusPresensi

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


def tentukan_status_waktu(lokasi: LokasiKantor, jam_saat_ini) -> str:
    """hadir vs telat, berdasarkan jam_masuk + toleransi_menit lokasi."""
    batas_telat = (
        datetime.combine(datetime.min, lokasi.jam_masuk) + timedelta(minutes=lokasi.toleransi_menit)
    ).time()
    return StatusPresensi.TELAT if jam_saat_ini > batas_telat else StatusPresensi.HADIR


@dataclass
class HasilCekWajah:
    lolos: bool
    alasan: Optional[str]
    skor_kemiripan: Optional[float]


def verifikasi_wajah(nidn, berkas_selfie) -> HasilCekWajah:
    """Syarat 2: selfie saat absen harus cocok dengan embedding hasil
    enrolment (presensi/face.py) DAN lolos pemeriksaan liveness dasar."""
    enrolment = EnrolmentWajah.objects.filter(nidn=nidn, consent_disetujui=True).first()
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
