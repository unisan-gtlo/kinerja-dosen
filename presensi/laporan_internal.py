"""Logika Laporan Presensi Internal -- laporan bulanan lintas-pegawai
untuk kebutuhan internal kampus (BEDA dari presensi/laporan_serdos.py
yang khusus format resmi LLDIKTI untuk dosen serdos). Bisa difilter per
kategori (dosen/tendik), fakultas, dan program studi. Menampilkan jam
Masuk & Pulang per hari (bukan paraf) -- makanya TIDAK dibatasi ke dosen
serdos saja, semua pegawai bisa masuk laporan ini.

Dipisah dari rekap.py karena bentuknya grid tanggal (seperti laporan
serdos), bukan agregat total jam kerja bulanan.
"""
from dataclasses import dataclass
from datetime import date

from django.db import DatabaseError
from django.utils import timezone

from master.models import Prodi
from simda_dosen.models import DataTendik
from simda_dosen.utils import attach_nama_resmi
from .laporan_serdos import jenis_tanggal_bulan
from .models import Presensi

# Pejabat struktural (Dekan/Wadek/Kaprodi/Sekprodi/Rektorat/Biro) SENGAJA
# digabung ke kategori "dosen" di LAPORAN ini -- secara kepegawaian
# mereka tetap dosen yang diberi tugas tambahan struktural, jadi tidak
# perlu jadi kategori terpisah untuk kebutuhan pelaporan internal.
# Catatan: ini CUMA soal pengelompokan tampilan laporan -- jam kerja
# presensi (KelompokPresensi "Dosen" vs "Pejabat", lihat CLAUDE.md § 9)
# TETAP terpisah seperti sebelumnya, tidak ikut berubah di sini.
KATEGORI_ROLES = {
    "dosen": ["dosen", "dekan", "wadek", "kaprodi", "sekprodi", "rektorat", "biro"],
    "tendik": ["tendik"],
}


@dataclass
class HariGridInternal:
    tanggal: date
    jenis: str  # "kerja" | "minggu" | "libur"
    jam_masuk: str  # "08:05" atau "" kalau tidak absen
    jam_pulang: str


def get_user_qs_laporan_internal(user_qs, kategori="", fakultas="", prodi=""):
    """Terapkan filter kategori/fakultas/prodi ke queryset User yang
    SUDAH di-scope cakupan (dapat_kelola) oleh pemanggil -- lihat
    presensi/views.py::_pengguna_dalam_cakupan, pola sama dengan
    Laporan Bulanan Jam Kerja."""
    if kategori in KATEGORI_ROLES:
        user_qs = user_qs.filter(role__in=KATEGORI_ROLES[kategori])
    if fakultas:
        user_qs = user_qs.filter(kode_fakultas=fakultas)
    if prodi:
        user_qs = user_qs.filter(kode_prodi=prodi)
    return user_qs


def _format_jam(waktu):
    if not waktu:
        return ""
    return timezone.localtime(waktu).strftime("%H:%M")


def data_laporan_internal(user_qs, bulan, tahun):
    """Return list (user, nama_prodi, hari_grid) -- satu per user dalam
    cakupan, urut nama. hari_grid: list HariGridInternal, jam kosong
    kalau tidak ada presensi tercatat hari itu (apa pun statusnya --
    laporan internal ini tampilkan apa adanya, tidak menyaring status
    seperti laporan serdos). `user.nama_resmi` (dari attach_nama_resmi)
    dipakai sebagai nama tampilan -- resolve dari SIMDA (DataDosen/
    DataTendik) supaya akun jabatan/administratif generik (mis. "Dekan
    Fikom") tidak nongol dengan nama jabatan, bukan nama orang.

    `nama_prodi` dobel fungsi tergantung role: Program Studi untuk dosen
    (termasuk pejabat struktural, prodi kosong kalau memang tidak
    tercatat), Unit Kerja untuk tendik (tendik tidak punya kode_prodi
    sama sekali, jadi kolom yang sama dipakai bareng di laporan supaya
    tidak perlu kolom terpisah -- lihat _label_kolom_instansi di
    laporan_internal_pdf.py untuk logika pilih label header)."""
    users = attach_nama_resmi(user_qs.order_by("first_name", "username"))
    jenis_per_tanggal = jenis_tanggal_bulan(bulan, tahun)

    prodi_map = {p.kode_prodi: p.nama_prodi for p in Prodi.objects.all()}

    nip_yayasan_set = {u.nip_yayasan for u in users if u.role == "tendik" and u.nip_yayasan}
    unit_kerja_by_nip = {}
    if nip_yayasan_set:
        try:
            unit_kerja_by_nip = {
                t.nip_yayasan: t.unit_kerja_nama
                for t in DataTendik.objects.using("simda").filter(nip_yayasan__in=nip_yayasan_set)
            }
        except DatabaseError:
            pass

    presensi_by_user = {}
    for p in Presensi.objects.filter(user__in=users, tanggal__year=tahun, tanggal__month=bulan):
        presensi_by_user.setdefault(p.user_id, {})[p.tanggal] = p

    hasil = []
    for u in users:
        presensi_tanggal = presensi_by_user.get(u.id, {})
        hari_grid = []
        for tanggal, jenis in jenis_per_tanggal:
            p = presensi_tanggal.get(tanggal)
            hari_grid.append(HariGridInternal(
                tanggal=tanggal, jenis=jenis,
                jam_masuk=_format_jam(p.waktu_masuk) if p else "",
                jam_pulang=_format_jam(p.waktu_pulang) if p else "",
            ))
        if u.role == "tendik":
            instansi = unit_kerja_by_nip.get(u.nip_yayasan, "") or ""
        else:
            instansi = prodi_map.get(u.kode_prodi, u.kode_prodi or "")
        hasil.append({
            "user": u,
            "nama_prodi": instansi,
            "hari_grid": hari_grid,
        })
    return hasil
