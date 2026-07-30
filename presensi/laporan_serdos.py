"""Logika penyusunan data Laporan Daftar Hadir Dosen Serdos (LLDIKTI).

Cuma dosen dengan Sertifikasi Dosen (serdos) berstatus DISETUJUI yang
masuk laporan ini (lihat presensi/utils.py::get_dosen_serdos_qs) --
judul dokumen resminya "DAFTAR HADIR DOSEN TETAP YAYASAN PENERIMA
SERDOS". Paraf yang ditempel adalah paraf digital yang sudah disimpan
dosen sekali lewat ParafDosen (auto-stamp, lihat presensi/models.py),
BUKAN digambar ulang tiap hari.

Dipisah dari presensi/views.py (dan dari rekap.py -- ini domainnya beda,
laporan kepatuhan LLDIKTI, bukan rekap jam kerja/payroll) supaya bisa
dipakai ulang oleh ekspor PDF maupun Excel tanpa terikat request/response
Django, dan supaya bisa dites langsung.
"""
import calendar
from dataclasses import dataclass
from datetime import date

from simda_dosen.models import DataDosen, GolonganPublik, JabatanFungsionalPublik

from .models import HariLibur, ParafDosen, Presensi, StatusPresensi, UrutanSerdos
from .utils import get_dosen_serdos_qs


@dataclass
class HariGrid:
    tanggal: date
    jenis: str  # "kerja" | "minggu" | "libur" -- non-"kerja" berarti diarsir, tanpa paraf
    hadir: bool


@dataclass
class BarisSerdos:
    user: object
    dosen_simda: object  # simda_dosen.DataDosen atau None (belum sinkron NIDN)
    gol_jabatan: str
    tugas_belajar: bool
    hari_grid: list
    total_hadir: int
    paraf: object  # ParafDosen atau None (belum pernah gambar paraf)


def _hari_dalam_bulan(bulan, tahun):
    jumlah_hari = calendar.monthrange(tahun, bulan)[1]
    return [date(tahun, bulan, hari) for hari in range(1, jumlah_hari + 1)]


def jenis_tanggal_bulan(bulan, tahun):
    """[(tanggal, jenis), ...] untuk tiap tanggal di bulan itu -- jenis
    "kerja"/"minggu"/"libur". SAMA untuk semua dosen (kalender institusi,
    bukan per-orang), jadi dipisah dari data_laporan_serdos supaya bisa
    dipakai ulang PDF/Excel untuk mengarsir kolom tanggal non-kerja tanpa
    perlu mengulang query HariLibur."""
    hari_libur_set = set(
        HariLibur.objects.filter(tanggal__year=tahun, tanggal__month=bulan).values_list("tanggal", flat=True)
    )
    hasil = []
    for tanggal in _hari_dalam_bulan(bulan, tahun):
        if tanggal in hari_libur_set:
            jenis = "libur"
        elif tanggal.weekday() == 6:
            jenis = "minggu"
        else:
            jenis = "kerja"
        hasil.append((tanggal, jenis))
    return hasil


def _gol_jabatan(dosen_simda, golongan_map, jabatan_map):
    """Rakit "III-C/Lektor" dari dua referensi SIMDA terpisah -- DataDosen
    cuma simpan id-nya (golongan_id/jabatan_fungsional_id), bukan teksnya
    langsung (lihat simda_dosen/models.py::golongan_nama/
    jabatan_fungsional_nama untuk pola serupa, tapi formatnya beda dari
    yang dibutuhkan laporan ini)."""
    if not dosen_simda:
        return ""
    golongan = golongan_map.get(dosen_simda.golongan_id)
    jabatan = jabatan_map.get(dosen_simda.jabatan_fungsional_id)
    if golongan and jabatan:
        return f"{golongan.kode}/{jabatan.nama}"
    return golongan.kode if golongan else (jabatan.nama if jabatan else "")


def data_laporan_serdos(bulan, tahun):
    """Return list BarisSerdos, satu per dosen serdos disetujui, terurut
    sesuai UrutanSerdos (yang belum diatur ditaruh di akhir, urut nama)."""
    dosen_users = list(get_dosen_serdos_qs().order_by("first_name", "username"))
    jenis_per_tanggal = jenis_tanggal_bulan(bulan, tahun)

    nidn_list = [u.nidn for u in dosen_users if u.nidn]
    dosen_simda_by_nidn = {
        d.nidn: d for d in DataDosen.objects.using("simda").filter(nidn__in=nidn_list)
    }
    golongan_map = {g.id: g for g in GolonganPublik.objects.using("simda").all()}
    jabatan_map = {j.id: j for j in JabatanFungsionalPublik.objects.using("simda").all()}

    urutan_map = {us.user_id: us.urutan for us in UrutanSerdos.objects.filter(user__in=dosen_users)}
    paraf_map = {p.user_id: p for p in ParafDosen.objects.filter(user__in=dosen_users)}

    hadir_by_user = {}
    for user_id, tanggal in Presensi.objects.filter(
        user__in=dosen_users, tanggal__year=tahun, tanggal__month=bulan,
        status__in=[StatusPresensi.HADIR, StatusPresensi.TELAT],
    ).values_list("user_id", "tanggal"):
        hadir_by_user.setdefault(user_id, set()).add(tanggal)

    baris_list = []
    for u in dosen_users:
        dosen_simda = dosen_simda_by_nidn.get(u.nidn)
        tugas_belajar = bool(dosen_simda and dosen_simda.status_kepegawaian_nama == "Tugas Belajar")
        tanggal_hadir = hadir_by_user.get(u.id, set())

        hari_grid = []
        total_hadir = 0
        for tanggal, jenis in jenis_per_tanggal:
            hadir = tanggal in tanggal_hadir
            if hadir:
                total_hadir += 1
            hari_grid.append(HariGrid(tanggal=tanggal, jenis=jenis, hadir=hadir))

        baris_list.append(BarisSerdos(
            user=u,
            dosen_simda=dosen_simda,
            gol_jabatan=_gol_jabatan(dosen_simda, golongan_map, jabatan_map),
            tugas_belajar=tugas_belajar,
            hari_grid=hari_grid,
            total_hadir=total_hadir,
            paraf=paraf_map.get(u.id),
        ))

    baris_list.sort(key=lambda b: (
        urutan_map.get(b.user.id) is None,
        urutan_map.get(b.user.id) or 0,
        b.user.get_full_name() or b.user.username,
    ))
    return baris_list
