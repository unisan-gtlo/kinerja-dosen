from django.db import models
from django.core.exceptions import ValidationError
from accounts.models import User
import os

SEMESTER_CHOICES = [
    ('Ganjil', 'Ganjil'),
    ('Genap', 'Genap'),
    ('Keduanya', 'Keduanya'),
]

def validate_bkd_file(value):
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ['.pdf', '.jpg', '.jpeg', '.png']:
        raise ValidationError('Hanya file PDF, JPG, dan PNG yang diizinkan.')
    if value.size > 5 * 1024 * 1024:
        raise ValidationError('Ukuran file maksimal 5MB.')

# BKD pindah ke simda_dosen.RiwayatBKD (ditulis langsung ke SIMDA) -- lihat
# simda_dosen/models.py. Fungsi di bawah TIDAK dipakai lagi tapi tetap
# dipertahankan karena migration lama (0003_bkd) merujuknya by-reference.
def upload_bkd(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f'bkd/{instance.user.username}/BKD_{instance.semester}_{instance.tahun_akademik}{ext}'


# Penelitian & Publikasi pindah ke app penelitian (lihat penelitian/models.py)
# -- dirombak mengikuti field spesifik SISTER (Penelitian.docx) + multi-
# anggota/penulis (Dosen/Mahasiswa/Kolaborator Eksternal), bukan lagi model
# generik flat. HKI juga pindah ke sana sebagai PatenHki.


# Pengabdian (PKM) pindah ke app pengabdian (lihat pengabdian/models.py) --
# dirombak mengikuti field spesifik SISTER (Pelaksanaan Pegabdian.docx) +
# multi-anggota (Dosen/Mahasiswa/Kolaborator Eksternal), plus 3 sub-fitur
# baru: Pembicara, Pengelola Jurnal, Jabatan Struktural.


# Pengajaran pindah ke app pendidikan (lihat pendidikan/models.py) --
# dipecah jadi Pengajaran/Bimbingan Mahasiswa/Pengujian Mahasiswa mengikuti
# field spesifik SISTER (Pengajaran.docx), bukan lagi 1 model generik.
# upload_* lama tidak ada untuk model ini jadi tidak perlu dipertahankan.


# Penghargaan & Kegiatan Penunjang pindah ke app penunjang (lihat
# penunjang/models.py) -- direklasifikasi jadi menu top-level "Penunjang"
# tersendiri (bukan bagian dari Data Kinerja), field dirombak mengikuti
# taksonomi SISTER asli (Penunjang.docx) plus Anggota Profesi (baru) dan
# fitur Anggota Kegiatan (Dosen) di Penunjang Lain.


def upload_dokumen_kinerja(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f'kinerja/dokumen/{instance.user.username}/{instance.jenis_kinerja}/{filename}'


class DokumenKinerja(models.Model):
    JENIS_KINERJA = [
        ('penelitian', 'Penelitian'),
        ('publikasi', 'Publikasi'),
        ('pkm', 'Pengabdian'),
        ('hki', 'HKI'),
        ('pembicara', 'Pembicara'),
        ('pengelola_jurnal', 'Pengelola Jurnal'),
        ('jabatan_struktural', 'Jabatan Struktural'),
        ('bkd', 'BKD'),
        ('pengajaran', 'Pengajaran'),
        ('bimbingan_mahasiswa', 'Bimbingan Mahasiswa'),
        ('pengujian_mahasiswa', 'Pengujian Mahasiswa'),
        ('bahan_ajar', 'Bahan Ajar'),
        ('pembinaan_mahasiswa', 'Pembinaan Mahasiswa'),
        ('orasi_ilmiah', 'Orasi Ilmiah'),
        ('tugas_tambahan', 'Tugas Tambahan'),
        ('anggota_profesi', 'Anggota Profesi'),
        ('penghargaan', 'Penghargaan'),
        ('penunjang', 'Kegiatan Penunjang'),
        ('diklat', 'Diklat'),
        ('sertifikasi', 'Sertifikasi'),
        ('tes', 'Tes'),
        ('beasiswa', 'Beasiswa'),
        ('kesejahteraan', 'Kesejahteraan'),
        ('tunjangan', 'Tunjangan'),
    ]
    JENIS_DOKUMEN = [
        ('surat_tugas', 'Surat Tugas'),
        ('kontrak', 'Kontrak/Perjanjian'),
        ('laporan_kemajuan', 'Laporan Kemajuan'),
        ('laporan_akhir', 'Laporan Akhir'),
        ('sertifikat', 'Sertifikat'),
        ('dokumentasi', 'Dokumentasi/Foto'),
        ('sk', 'SK/Keputusan'),
        ('lainnya', 'Lainnya'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='dokumen_kinerja_set'
    )
    jenis_kinerja = models.CharField(max_length=20, choices=JENIS_KINERJA)
    kinerja_id = models.IntegerField()
    jenis_dokumen = models.CharField(max_length=20, choices=JENIS_DOKUMEN)
    nama_dokumen = models.CharField(max_length=200)
    keterangan = models.TextField(blank=True, null=True)
    file_dokumen = models.FileField(
        upload_to=upload_dokumen_kinerja,
        blank=True, null=True,
        help_text='PDF/JPG/PNG max 5MB'
    )
    link_dokumen = models.URLField(blank=True, null=True)
    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Dokumen Kinerja'
        verbose_name_plural = 'Dokumen Kinerja'
        ordering = ['jenis_dokumen', 'nama_dokumen']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.jenis_kinerja} - {self.nama_dokumen}"

    @property
    def tersedia(self):
        return bool(self.file_dokumen or self.link_dokumen)