"""Perhitungan untuk dashboard admin/HR & tabel data presensi harian --
dipisah dari views.py supaya logikanya bisa dites & dipakai ulang (mis.
oleh ekspor Excel) tanpa terikat request/response Django.

Catatan cakupan: SAAT INI DOSEN SAJA (kunci NIDN). Staf/tendik belum
tercakup karena seluruh presensi masih dikunci NIDN (lihat CLAUDE.md --
migrasi ke kunci accounts.User yang mencakup staf direncanakan menyusul).
"""
from datetime import timedelta

from django.utils import timezone

from .models import Presensi, StatusPresensi

NAMA_HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def _nidn_list(dosen_qs):
    return list(dosen_qs.exclude(nidn__isnull=True).exclude(nidn="").values_list("nidn", flat=True))


def ringkasan_hari_ini(nidn_list, tanggal=None):
    """KPI ringkas: total, hadir, telat, belum absen, ditandai -- untuk satu tanggal."""
    tanggal = tanggal or timezone.localdate()
    presensi_hari_ini = Presensi.objects.filter(nidn__in=nidn_list, tanggal=tanggal)

    hadir = presensi_hari_ini.filter(status=StatusPresensi.HADIR).count()
    telat = presensi_hari_ini.filter(status=StatusPresensi.TELAT).count()
    ditandai = presensi_hari_ini.filter(ditandai=True).count()
    sudah_absen = presensi_hari_ini.values_list("nidn", flat=True).distinct().count()

    return {
        "tanggal": tanggal,
        "total": len(nidn_list),
        "hadir": hadir,
        "telat": telat,
        "ditandai": ditandai,
        "belum_absen": max(len(nidn_list) - sudah_absen, 0),
    }


def tren_mingguan(nidn_list, jumlah_hari=6, tanggal_akhir=None):
    """Jumlah hadir (tepat waktu atau telat -- pokoknya masuk) per hari,
    N hari terakhir sampai tanggal_akhir (default hari ini)."""
    tanggal_akhir = tanggal_akhir or timezone.localdate()
    hasil = []
    for i in range(jumlah_hari - 1, -1, -1):
        tanggal = tanggal_akhir - timedelta(days=i)
        jumlah = Presensi.objects.filter(
            nidn__in=nidn_list, tanggal=tanggal,
            status__in=[StatusPresensi.HADIR, StatusPresensi.TELAT],
        ).count()
        hasil.append({"tanggal": tanggal, "label": NAMA_HARI[tanggal.weekday()][:3], "jumlah": jumlah})
    return hasil


def top_telat_hari_ini(nidn_list, tanggal=None, batas=5):
    """Daftar presensi telat, diurutkan dari yang paling telat."""
    tanggal = tanggal or timezone.localdate()
    antrian = (
        Presensi.objects.filter(nidn__in=nidn_list, tanggal=tanggal, status=StatusPresensi.TELAT)
        .exclude(waktu_masuk__isnull=True)
        .select_related("lokasi")
    )
    daftar = []
    for p in antrian:
        menit_telat = None
        if p.lokasi:
            waktu_lokal = timezone.localtime(p.waktu_masuk)
            batas_masuk = waktu_lokal.replace(
                hour=p.lokasi.jam_masuk.hour, minute=p.lokasi.jam_masuk.minute,
                second=0, microsecond=0,
            )
            menit_telat = int((waktu_lokal - batas_masuk).total_seconds() // 60)
        daftar.append({"presensi": p, "menit_telat": menit_telat})
    daftar.sort(key=lambda d: d["menit_telat"] or 0, reverse=True)
    return daftar[:batas]


def data_presensi_harian(dosen_qs, tanggal):
    """Satu baris per dosen dalam cakupan (bukan cuma yang sudah absen) --
    supaya yang belum absen sama sekali tetap kelihatan di tabel/ekspor."""
    nidn_list = _nidn_list(dosen_qs)
    presensi_by_nidn = {
        p.nidn: p for p in Presensi.objects.filter(nidn__in=nidn_list, tanggal=tanggal).select_related("lokasi")
    }
    daftar = []
    for dosen in dosen_qs:
        if not dosen.nidn:
            continue
        daftar.append({"dosen": dosen, "presensi": presensi_by_nidn.get(dosen.nidn)})
    return daftar
