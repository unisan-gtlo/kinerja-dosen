from django.db import models
from django.core.exceptions import ValidationError
import os
from accounts.models import User

# Profil identitas, Riwayat Jabatan Fungsional, dan Riwayat Pendidikan pindah
# ke simda_dosen (model unmanaged, ditulis langsung ke SIMDA) -- lihat
# simda_dosen/models.py. Sertifikat & DokumenLain tetap lokal di SIKD.

def validate_file(value):
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ['.pdf', '.jpg', '.jpeg', '.png']:
        raise ValidationError('Hanya file PDF, JPG, dan PNG yang diizinkan.')
    if value.size > 5 * 1024 * 1024:
        raise ValidationError('Ukuran file maksimal 5MB.')

def upload_sertifikat(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f'sertifikat/{instance.user.username}/{filename}'

def upload_dokumen(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f'dokumen/{instance.user.username}/{filename}'

# Fungsi upload_* di bawah ini TIDAK dipakai lagi (ProfilDosen/RiwayatJabfung/
# RiwayatPendidikan sudah pindah ke simda_dosen) -- tapi tetap dipertahankan
# karena migration lama (0002) merujuk fungsi ini by-reference. Menghapusnya
# akan bikin `makemigrations`/`migrate` gagal load riwayat migrasi.
def upload_profil(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f'profil/{instance.user.username}/foto{ext}'

def upload_ktp(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f'profil/{instance.user.username}/ktp{ext}'

def upload_npwp(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f'profil/{instance.user.username}/npwp{ext}'

def upload_sk_yayasan(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f'profil/{instance.user.username}/sk_yayasan{ext}'

def upload_jabfung(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f'jabfung/{instance.user.username}/{filename}'

def upload_ijazah(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f'pendidikan/{instance.user.username}/ijazah_{instance.jenjang}{ext}'

def upload_transkrip(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f'pendidikan/{instance.user.username}/transkrip_{instance.jenjang}{ext}'


class Sertifikat(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='sertifikat_set'
    )
    jenis_sertifikat = models.CharField(
        max_length=20,
        choices=[
            ('Serdos', 'Sertifikat Dosen'),
            ('Kompetensi', 'Kompetensi'),
            ('Profesi', 'Profesi'),
            ('Internasional', 'Internasional'),
            ('Lainnya', 'Lainnya')
        ]
    )
    nama_sertifikat = models.CharField(max_length=200)
    no_sertifikat = models.CharField(max_length=100, blank=True, null=True)
    lembaga_penerbit = models.CharField(max_length=100, blank=True, null=True)
    tahun_terbit = models.IntegerField(blank=True, null=True)
    masa_berlaku = models.CharField(max_length=20, blank=True, null=True)
    file_sertifikat = models.FileField(
        upload_to=upload_sertifikat,
        validators=[validate_file],
        blank=True, null=True
    )
    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Sertifikat'
        verbose_name_plural = 'Sertifikat'
        ordering = ['-tahun_terbit']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.nama_sertifikat}"


class DokumenLain(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='dokumen_set'
    )
    jenis_dokumen = models.CharField(max_length=50)
    nama_dokumen = models.CharField(max_length=200)
    no_dokumen = models.CharField(max_length=100, blank=True, null=True)
    tgl_terbit = models.DateField(blank=True, null=True)
    keterangan = models.TextField(blank=True, null=True)
    file_dokumen = models.FileField(
        upload_to=upload_dokumen,
        validators=[validate_file],
        blank=True, null=True
    )
    link_dokumen = models.URLField(blank=True, null=True)
    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Dokumen Lain'
        verbose_name_plural = 'Dokumen Lain'
        ordering = ['-tgl_input']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.nama_dokumen}"
