"""Perhitungan untuk dashboard admin/HR & tabel data presensi harian --
dipisah dari views.py supaya logikanya bisa dites & dipakai ulang (mis.
oleh ekspor Excel) tanpa terikat request/response Django.

Catatan cakupan: skema presensi sekarang dikunci `user` (accounts.User),
jadi SUDAH mendukung staf/tendik di level data. Dashboard & tabel di
bawah ini masih memanggil `laporan.views.get_dosen_queryset` (dosen-only)
lewat presensi/views.py -- kalau nanti staf perlu ditampilkan juga,
tinggal ganti sumber queryset user-nya di views.py, TIDAK perlu ubah
fungsi-fungsi di modul ini (semua sudah generik berbasis user, bukan NIDN).
"""
from datetime import timedelta

from django.utils import timezone

from .models import Presensi, StatusPresensi

NAMA_HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def ringkasan_hari_ini(user_ids, tanggal=None):
    """KPI ringkas: total, hadir, telat, belum absen, ditandai -- untuk satu tanggal."""
    tanggal = tanggal or timezone.localdate()
    presensi_hari_ini = Presensi.objects.filter(user_id__in=user_ids, tanggal=tanggal)

    hadir = presensi_hari_ini.filter(status=StatusPresensi.HADIR).count()
    telat = presensi_hari_ini.filter(status=StatusPresensi.TELAT).count()
    ditandai = presensi_hari_ini.filter(ditandai=True).count()
    sudah_absen = presensi_hari_ini.values_list("user_id", flat=True).distinct().count()

    return {
        "tanggal": tanggal,
        "total": len(user_ids),
        "hadir": hadir,
        "telat": telat,
        "ditandai": ditandai,
        "belum_absen": max(len(user_ids) - sudah_absen, 0),
    }


def tren_mingguan(user_ids, jumlah_hari=6, tanggal_akhir=None):
    """Jumlah hadir (tepat waktu atau telat -- pokoknya masuk) per hari,
    N hari terakhir sampai tanggal_akhir (default hari ini)."""
    tanggal_akhir = tanggal_akhir or timezone.localdate()
    hasil = []
    for i in range(jumlah_hari - 1, -1, -1):
        tanggal = tanggal_akhir - timedelta(days=i)
        jumlah = Presensi.objects.filter(
            user_id__in=user_ids, tanggal=tanggal,
            status__in=[StatusPresensi.HADIR, StatusPresensi.TELAT],
        ).count()
        hasil.append({"tanggal": tanggal, "label": NAMA_HARI[tanggal.weekday()][:3], "jumlah": jumlah})
    return hasil


def top_telat_hari_ini(user_ids, tanggal=None, batas=5):
    """Daftar presensi telat, diurutkan dari yang paling telat."""
    tanggal = tanggal or timezone.localdate()
    antrian = (
        Presensi.objects.filter(user_id__in=user_ids, tanggal=tanggal, status=StatusPresensi.TELAT)
        .exclude(waktu_masuk__isnull=True)
        .select_related("lokasi", "user")
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
    """Satu baris per orang dalam cakupan (bukan cuma yang sudah absen) --
    supaya yang belum absen sama sekali tetap kelihatan di tabel/ekspor."""
    user_ids = list(dosen_qs.values_list("id", flat=True))
    presensi_by_user = {
        p.user_id: p for p in Presensi.objects.filter(user_id__in=user_ids, tanggal=tanggal).select_related("lokasi")
    }
    return [{"dosen": orang, "presensi": presensi_by_user.get(orang.id)} for orang in dosen_qs]
