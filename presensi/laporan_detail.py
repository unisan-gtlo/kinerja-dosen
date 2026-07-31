"""Detail Presensi Bulanan -- laporan drill-down OPSIONAL untuk melihat
presensi SATU pegawai tertentu (dicari lewat nama/NIDN) secara rinci per
hari dalam satu bulan, dilengkapi ringkasan total jam kerja vs target.

BEDA dari 3 laporan presensi lain (Laporan Bulanan Jam Kerja, Laporan
Presensi Internal, Laporan Daftar Hadir Serdos) yang semuanya menampilkan
BANYAK pegawai sekaligus -- ini justru kebalikannya: cari 1 orang dulu,
baru lihat detailnya. Dipakai kalau HR/atasan perlu mengecek riwayat
kehadiran seseorang secara spesifik (mis. ada yang dipertanyakan), bukan
untuk pemakaian rutin.

Reuse rekap_bulanan_user (presensi/rekap.py) untuk ringkasan total/
target/selisih -- tidak menghitung ulang dari nol.
"""
from dataclasses import dataclass
from datetime import date, timedelta

from django.db.models import Q
from django.utils import timezone

from .laporan_serdos import jenis_tanggal_bulan
from .models import IzinCuti, Presensi
from .rekap import rekap_bulanan_user

NAMA_HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


@dataclass
class BarisDetailHarian:
    tanggal: date
    nama_hari: str
    jenis: str  # "kerja" | "minggu" | "libur"
    status: str
    waktu_masuk: str
    waktu_pulang: str
    keterangan: str
    durasi_kerja: str


def cari_pegawai(user_qs, kata_kunci):
    """Cari pegawai dalam cakupan (user_qs SUDAH di-scope dapat_kelola
    oleh pemanggil) lewat nama depan/belakang/username/NIDN."""
    kata_kunci = (kata_kunci or "").strip()
    if not kata_kunci:
        return user_qs.none()
    return user_qs.filter(
        Q(first_name__icontains=kata_kunci) | Q(last_name__icontains=kata_kunci)
        | Q(username__icontains=kata_kunci) | Q(nidn__icontains=kata_kunci)
    ).distinct().order_by("first_name", "username")


def _format_jam(waktu):
    return timezone.localtime(waktu).strftime("%H:%M") if waktu else "-"


def _keterangan_hari(presensi):
    """Gabungan label granular (terlambat/lebih awal/pulang cepat/lembur)
    -- pola sama seperti templates/presensi/riwayat.html, tapi dirakit
    jadi satu string supaya gampang ditaruh di 1 kolom tabel/ekspor."""
    bagian = []
    if presensi.menit_terlambat > 0:
        bagian.append(f"Terlambat {presensi.menit_terlambat} menit")
    if presensi.menit_lebih_awal > 0:
        bagian.append(f"Datang {presensi.menit_lebih_awal} menit lebih awal")
    if presensi.menit_pulang_cepat > 0:
        bagian.append(f"Pulang {presensi.menit_pulang_cepat} menit lebih cepat")
    if presensi.menit_lembur > 0:
        label_status = {
            "menunggu": "menunggu persetujuan", "disetujui": "disetujui", "ditolak": "ditolak",
        }.get(presensi.status_lembur, "")
        teks = f"Lembur {presensi.menit_lembur} menit"
        if label_status:
            teks += f" ({label_status})"
        bagian.append(teks)
    return "; ".join(bagian) if bagian else "-"


def detail_presensi_bulanan(user, bulan, tahun):
    """Return dict {"rekap": .., "baris": [BarisDetailHarian, ...]} --
    SATU baris per TANGGAL kalender bulan itu (termasuk hari libur/
    minggu dan hari kerja tanpa presensi = dianggap Alpa), bukan cuma
    tanggal yang kebetulan ada datanya -- supaya gambarannya lengkap
    untuk pengecekan HR."""
    jenis_per_tanggal = jenis_tanggal_bulan(bulan, tahun)
    presensi_by_tanggal = {
        p.tanggal: p for p in Presensi.objects.filter(
            user=user, tanggal__year=tahun, tanggal__month=bulan,
        ).select_related("kelompok", "lokasi")
    }

    awal_bulan = jenis_per_tanggal[0][0]
    akhir_bulan = jenis_per_tanggal[-1][0]
    izin_by_tanggal = {}
    for izin in IzinCuti.objects.filter(
        user=user, status=IzinCuti.StatusApproval.DISETUJUI,
        tanggal_mulai__lte=akhir_bulan, tanggal_selesai__gte=awal_bulan,
    ):
        hari = max(izin.tanggal_mulai, awal_bulan)
        selesai = min(izin.tanggal_selesai, akhir_bulan)
        while hari <= selesai:
            izin_by_tanggal[hari] = izin
            hari += timedelta(days=1)

    baris = []
    for tanggal, jenis in jenis_per_tanggal:
        nama_hari = NAMA_HARI[tanggal.weekday()]
        presensi = presensi_by_tanggal.get(tanggal)
        izin = izin_by_tanggal.get(tanggal)

        if presensi:
            baris.append(BarisDetailHarian(
                tanggal=tanggal, nama_hari=nama_hari, jenis=jenis,
                status=presensi.get_status_display(),
                waktu_masuk=_format_jam(presensi.waktu_masuk),
                waktu_pulang=_format_jam(presensi.waktu_pulang),
                keterangan=_keterangan_hari(presensi),
                durasi_kerja=presensi.durasi_kerja if presensi.waktu_pulang else "-",
            ))
        elif izin:
            baris.append(BarisDetailHarian(
                tanggal=tanggal, nama_hari=nama_hari, jenis=jenis,
                status=izin.get_tipe_display(), waktu_masuk="-", waktu_pulang="-",
                keterangan=izin.alasan or "-", durasi_kerja="-",
            ))
        elif jenis != "kerja":
            baris.append(BarisDetailHarian(
                tanggal=tanggal, nama_hari=nama_hari, jenis=jenis,
                status="Libur", waktu_masuk="-", waktu_pulang="-", keterangan="-", durasi_kerja="-",
            ))
        else:
            baris.append(BarisDetailHarian(
                tanggal=tanggal, nama_hari=nama_hari, jenis=jenis,
                status="Alpa", waktu_masuk="-", waktu_pulang="-", keterangan="-", durasi_kerja="-",
            ))

    return {"rekap": rekap_bulanan_user(user, bulan, tahun), "baris": baris}
