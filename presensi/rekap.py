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

from .models import Presensi, StatusPresensi, TargetKerjaBulanan, format_jam_menit

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
    """Daftar presensi telat, diurutkan dari yang paling telat.

    Pakai Presensi.menit_terlambat yang SUDAH dihitung & disimpan saat
    absen masuk (lihat presensi/decision.py::hitung_ketepatan_masuk) --
    kelompok-aware (prioritas jam kelompok di atas lokasi), bukan dihitung
    ulang dari lokasi.jam_masuk saja seperti sebelumnya."""
    tanggal = tanggal or timezone.localdate()
    antrian = (
        Presensi.objects.filter(user_id__in=user_ids, tanggal=tanggal, status=StatusPresensi.TELAT)
        .exclude(waktu_masuk__isnull=True)
        .select_related("lokasi", "kelompok", "user")
        .order_by("-menit_terlambat")[:batas]
    )
    return [{"presensi": p, "menit_telat": p.menit_terlambat} for p in antrian]


def format_selisih_jam_menit(selisih_menit):
    """Format selisih (boleh negatif -- kurang dari target) jadi "+JJ:MM"
    / "-JJ:MM". None kalau tidak ada target untuk dibandingkan."""
    if selisih_menit is None:
        return None
    tanda = "-" if selisih_menit < 0 else "+"
    return f"{tanda}{format_jam_menit(abs(selisih_menit))}"


def rekap_bulanan_user(user, bulan, tahun):
    """Ringkasan realisasi jam kerja sebulan untuk satu user, dibandingkan
    ke TargetKerjaBulanan kelompoknya -- dasar penggajian (CLAUDE.md § 9).

    Presensi yang DITOLAK dikecualikan (tidak ada durasi kerja sah).
    Kelompok dipakai dari snapshot presensi (baris pertama bulan itu yang
    punya kelompok) -- kalau tidak ada satupun presensi berkelompok di
    bulan itu (mis. belum absen sama sekali), target ikut kosong.
    """
    presensi_bulan = list(
        Presensi.objects.filter(user=user, tanggal__year=tahun, tanggal__month=bulan)
        .exclude(status=StatusPresensi.DITOLAK)
        .select_related("kelompok")
    )
    total_menit = sum(p.durasi_kerja_menit for p in presensi_bulan)
    kelompok = next((p.kelompok for p in presensi_bulan if p.kelompok), None)
    target = (
        TargetKerjaBulanan.objects.filter(kelompok=kelompok, bulan=bulan, tahun=tahun).first()
        if kelompok else None
    )
    selisih_menit = int(total_menit - target.target_jam_kerja * 60) if target else None

    return {
        "hari_hadir": len(presensi_bulan),
        "total_menit": total_menit,
        "total_jam_kerja": format_jam_menit(total_menit),
        "kelompok": kelompok,
        "target": target,
        "selisih_menit": selisih_menit,
        "selisih_jam_kerja": format_selisih_jam_menit(selisih_menit),
    }


def laporan_bulanan_jam_kerja(user_qs, bulan, tahun):
    """Satu baris per user dalam cakupan yang PUNYA presensi di bulan itu
    -- laporan lintas-pegawai (dosen + staf) untuk dasar penggajian, lihat
    CLAUDE.md § 9. Beda dengan data_presensi_harian (1 baris per hari per
    orang, termasuk yang belum absen): di sini 1 baris per orang per bulan,
    dan yang tanpa presensi sama sekali di bulan itu tidak ikut tampil."""
    user_ids_ada_presensi = (
        Presensi.objects.filter(user__in=user_qs, tanggal__year=tahun, tanggal__month=bulan)
        .values_list("user_id", flat=True).distinct()
    )
    baris = [
        {"user": u, **rekap_bulanan_user(u, bulan, tahun)}
        for u in user_qs.filter(id__in=user_ids_ada_presensi)
    ]
    baris.sort(key=lambda b: b["user"].get_full_name() or b["user"].username)
    return baris


def data_presensi_harian(dosen_qs, tanggal):
    """Satu baris per orang dalam cakupan (bukan cuma yang sudah absen) --
    supaya yang belum absen sama sekali tetap kelihatan di tabel/ekspor."""
    user_ids = list(dosen_qs.values_list("id", flat=True))
    presensi_by_user = {
        p.user_id: p for p in Presensi.objects.filter(user_id__in=user_ids, tanggal=tanggal)
        .select_related("lokasi", "kelompok")
    }
    return [{"dosen": orang, "presensi": presensi_by_user.get(orang.id)} for orang in dosen_qs]
