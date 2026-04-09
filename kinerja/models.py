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

def upload_bkd(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f'bkd/{instance.user.username}/BKD_{instance.semester}_{instance.tahun_akademik}{ext}'


class BKD(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='bkd_set'
    )
    kode_prodi = models.CharField(max_length=10, blank=True, null=True)
    kode_fakultas = models.CharField(max_length=10, blank=True, null=True)
    semester = models.CharField(
        max_length=10,
        choices=[('Ganjil', 'Ganjil'), ('Genap', 'Genap')]
    )
    tahun_akademik = models.CharField(max_length=10)
    file_bkd = models.FileField(
        upload_to=upload_bkd,
        validators=[validate_bkd_file],
        blank=True, null=True,
        help_text='Upload file PDF BKD dari SISTER (max 5MB)'
    )
    link_bkd = models.URLField(
        blank=True, null=True,
        help_text='Atau isi link Google Drive'
    )
    keterangan = models.TextField(blank=True, null=True)
    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'BKD'
        verbose_name_plural = 'BKD'
        ordering = ['-tahun_akademik', 'semester']
        unique_together = ['user', 'semester', 'tahun_akademik']

    def __str__(self):
        return f"{self.user.get_full_name()} - BKD {self.semester} {self.tahun_akademik}"

    @property
    def bukti_tersedia(self):
        return bool(self.file_bkd or self.link_bkd)

    @property
    def periode(self):
        return f"{self.semester} {self.tahun_akademik}"


class Penelitian(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='penelitian_set'
    )
    kode_prodi = models.CharField(max_length=10)
    kode_fakultas = models.CharField(max_length=10)
    judul = models.TextField()
    jml_mahasiswa = models.IntegerField(default=0)
    jenis_hibah = models.CharField(max_length=100, blank=True, null=True)
    sumber = models.CharField(max_length=100, blank=True, null=True)
    durasi = models.IntegerField(default=1)
    ln_i = models.CharField(
        max_length=5,
        choices=[('L', 'Lokal'), ('N', 'Nasional'), ('I', 'Internasional')],
        blank=True, null=True
    )
    semester = models.CharField(
        max_length=10, choices=SEMESTER_CHOICES,
        blank=True, null=True
    )
    tahun_akademik = models.CharField(max_length=10)
    pendanaan = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    link_bukti = models.URLField(blank=True, null=True)
    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Penelitian'
        verbose_name_plural = 'Penelitian'
        ordering = ['-tahun_akademik', 'semester']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.judul[:50]}"

    @property
    def periode(self):
        if self.semester:
            return f"{self.semester} {self.tahun_akademik}"
        return self.tahun_akademik


class Publikasi(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='publikasi_set'
    )
    kode_prodi = models.CharField(max_length=10)
    kode_fakultas = models.CharField(max_length=10)
    judul = models.TextField()
    jenis_publikasi = models.CharField(
        max_length=5,
        choices=[
            ('IB', 'Internasional Bereputasi'),
            ('I', 'Internasional'),
            ('S1', 'Sinta 1'), ('S2', 'Sinta 2'),
            ('S3', 'Sinta 3'), ('S4', 'Sinta 4'),
            ('T', 'Tidak Terakreditasi')
        ]
    )
    nama_jurnal = models.CharField(max_length=200, blank=True, null=True)
    volume = models.CharField(max_length=20, blank=True, null=True)
    nomor = models.CharField(max_length=20, blank=True, null=True)
    halaman = models.CharField(max_length=20, blank=True, null=True)
    tahun_terbit = models.IntegerField(blank=True, null=True)
    semester = models.CharField(
        max_length=10, choices=SEMESTER_CHOICES,
        blank=True, null=True
    )
    tahun_akademik = models.CharField(max_length=10)
    link_bukti = models.URLField(blank=True, null=True)
    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Publikasi'
        verbose_name_plural = 'Publikasi'
        ordering = ['-tahun_akademik', 'semester']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.judul[:50]}"

    @property
    def periode(self):
        if self.semester:
            return f"{self.semester} {self.tahun_akademik}"
        return self.tahun_akademik


class PKM(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='pkm_set'
    )
    kode_prodi = models.CharField(max_length=10)
    kode_fakultas = models.CharField(max_length=10)
    judul = models.TextField()
    jml_mahasiswa = models.IntegerField(default=0)
    jenis_hibah = models.CharField(max_length=100, blank=True, null=True)
    sumber = models.CharField(max_length=100, blank=True, null=True)
    durasi = models.IntegerField(default=1)
    ln_i = models.CharField(
        max_length=5,
        choices=[('L', 'Lokal'), ('N', 'Nasional'), ('I', 'Internasional')],
        blank=True, null=True
    )
    semester = models.CharField(
        max_length=10, choices=SEMESTER_CHOICES,
        blank=True, null=True
    )
    tahun_akademik = models.CharField(max_length=10)
    pendanaan = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    link_bukti = models.URLField(blank=True, null=True)
    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Pengabdian Masyarakat'
        verbose_name_plural = 'Pengabdian Masyarakat'
        ordering = ['-tahun_akademik', 'semester']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.judul[:50]}"

    @property
    def periode(self):
        if self.semester:
            return f"{self.semester} {self.tahun_akademik}"
        return self.tahun_akademik


class HKI(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='hki_set'
    )
    kode_prodi = models.CharField(max_length=10)
    kode_fakultas = models.CharField(max_length=10)
    judul = models.TextField()
    jenis_hki = models.CharField(
        max_length=30,
        choices=[
            ('Paten', 'Paten'),
            ('Paten Sederhana', 'Paten Sederhana'),
            ('Hak Cipta', 'Hak Cipta'),
            ('Merek', 'Merek'),
            ('Desain Industri', 'Desain Industri'),
            ('Lainnya', 'Lainnya')
        ]
    )
    no_hki = models.CharField(max_length=100, blank=True, null=True)
    tahun_perolehan = models.IntegerField(blank=True, null=True)
    semester = models.CharField(
        max_length=10, choices=SEMESTER_CHOICES,
        blank=True, null=True
    )
    tahun_akademik = models.CharField(max_length=10)
    link_bukti = models.URLField(blank=True, null=True)
    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'HKI'
        verbose_name_plural = 'HKI'
        ordering = ['-tahun_akademik', 'semester']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.judul[:50]}"

    @property
    def periode(self):
        if self.semester:
            return f"{self.semester} {self.tahun_akademik}"
        return self.tahun_akademik