from django.db import models
from django.core.exceptions import ValidationError
import os
from accounts.models import User

def validate_file(value):
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ['.pdf', '.jpg', '.jpeg', '.png']:
        raise ValidationError('Hanya file PDF, JPG, dan PNG yang diizinkan.')
    if value.size > 5 * 1024 * 1024:
        raise ValidationError('Ukuran file maksimal 5MB.')

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

def upload_sertifikat(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f'sertifikat/{instance.user.username}/{filename}'

def upload_dokumen(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f'dokumen/{instance.user.username}/{filename}'

def upload_bkd(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f'bkd/{instance.user.username}/BKD_{instance.semester}_{instance.tahun_akademik}{ext}'

class ProfilDosen(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profil'
    )
    nik = models.CharField(max_length=20, blank=True, null=True)
    tempat_lahir = models.CharField(max_length=50, blank=True, null=True)
    tgl_lahir = models.DateField(blank=True, null=True)
    jenis_kelamin = models.CharField(
        max_length=10,
        choices=[('L', 'Laki-laki'), ('P', 'Perempuan')],
        blank=True, null=True
    )
    agama = models.CharField(
        max_length=20,
        choices=[
            ('Islam', 'Islam'), ('Kristen', 'Kristen'),
            ('Katolik', 'Katolik'), ('Hindu', 'Hindu'),
            ('Buddha', 'Buddha'), ('Konghucu', 'Konghucu')
        ],
        blank=True, null=True
    )
    status_pernikahan = models.CharField(
        max_length=20,
        choices=[
            ('Belum Menikah', 'Belum Menikah'),
            ('Menikah', 'Menikah'),
            ('Cerai', 'Cerai')
        ],
        blank=True, null=True
    )
    alamat = models.TextField(blank=True, null=True)
    email_pribadi = models.EmailField(blank=True, null=True)
    jabfung_aktif = models.CharField(
        max_length=30,
        choices=[
            ('Tenaga Pengajar', 'Tenaga Pengajar'),
            ('Asisten Ahli', 'Asisten Ahli'),
            ('Lektor', 'Lektor'),
            ('Lektor Kepala', 'Lektor Kepala'),
            ('Guru Besar', 'Guru Besar')
        ],
        blank=True, null=True
    )
    pendidikan_terakhir = models.CharField(
        max_length=5,
        choices=[('S1', 'S1'), ('S2', 'S2'), ('S3', 'S3')],
        blank=True, null=True
    )
    bidang_keahlian = models.CharField(max_length=100, blank=True, null=True)
    mata_kuliah_diampu = models.TextField(blank=True, null=True)

    # Upload langsung — file kecil
    foto = models.ImageField(
        upload_to=upload_profil,
        validators=[validate_file],
        blank=True, null=True
    )
    file_ktp = models.FileField(
        upload_to=upload_ktp,
        validators=[validate_file],
        blank=True, null=True
    )
    file_npwp = models.FileField(
        upload_to=upload_npwp,
        validators=[validate_file],
        blank=True, null=True
    )
    file_sk_yayasan = models.FileField(
        upload_to=upload_sk_yayasan,
        validators=[validate_file],
        blank=True, null=True
    )

    # Link Drive — untuk dokumen tambahan
    link_dokumen_lain = models.URLField(blank=True, null=True)

    tgl_update = models.DateTimeField(auto_now=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Profil Dosen'
        verbose_name_plural = 'Profil Dosen'

    def __str__(self):
        return f"Profil - {self.user.get_full_name()}"

    @property
    def persentase_kelengkapan(self):
        fields = [
            self.nik, self.tempat_lahir, self.tgl_lahir,
            self.jenis_kelamin, self.agama, self.alamat,
            self.email_pribadi, self.jabfung_aktif,
            self.pendidikan_terakhir, self.bidang_keahlian,
            self.foto, self.file_ktp, self.file_sk_yayasan
        ]
        filled = sum(1 for f in fields if f)
        return int((filled / len(fields)) * 100)


class RiwayatJabfung(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='jabfung_set'
    )
    jabatan = models.CharField(
        max_length=30,
        choices=[
            ('Tenaga Pengajar', 'Tenaga Pengajar'),
            ('Asisten Ahli', 'Asisten Ahli'),
            ('Lektor', 'Lektor'),
            ('Lektor Kepala', 'Lektor Kepala'),
            ('Guru Besar', 'Guru Besar')
        ]
    )
    no_sk = models.CharField(max_length=100, blank=True, null=True)
    tgl_sk = models.DateField(blank=True, null=True)
    tmt_berlaku = models.DateField(blank=True, null=True)
    instansi_penerbit = models.CharField(max_length=100, blank=True, null=True)

    # Upload SK langsung
    file_sk = models.FileField(
        upload_to=upload_jabfung,
        validators=[validate_file],
        blank=True, null=True
    )
    # Atau link Drive jika file besar
    link_sk = models.URLField(blank=True, null=True)

    status = models.CharField(
        max_length=10,
        choices=[('aktif', 'Aktif'), ('nonaktif', 'Nonaktif')],
        default='aktif'
    )
    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Riwayat Jabatan Fungsional'
        verbose_name_plural = 'Riwayat Jabatan Fungsional'
        ordering = ['-tgl_sk']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.jabatan}"

    @property
    def bukti_tersedia(self):
        return bool(self.file_sk or self.link_sk)


class RiwayatPendidikan(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='pendidikan_set'
    )
    jenjang = models.CharField(
        max_length=5,
        choices=[
            ('S1', 'S1'), ('S2', 'S2'), ('S3', 'S3'),
            ('D3', 'D3'), ('D4', 'D4')
        ]
    )
    bidang_ilmu = models.CharField(max_length=100)
    nama_pt = models.CharField(max_length=100)
    kota_pt = models.CharField(max_length=50, blank=True, null=True)
    negara = models.CharField(max_length=50, default='Indonesia')
    tahun_masuk = models.IntegerField(blank=True, null=True)
    tahun_lulus = models.IntegerField(blank=True, null=True)
    no_ijazah = models.CharField(max_length=50, blank=True, null=True)

    # Upload ijazah & transkrip langsung
    file_ijazah = models.FileField(
        upload_to=upload_ijazah,
        validators=[validate_file],
        blank=True, null=True
    )
    file_transkrip = models.FileField(
        upload_to=upload_transkrip,
        validators=[validate_file],
        blank=True, null=True
    )

    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Riwayat Pendidikan'
        verbose_name_plural = 'Riwayat Pendidikan'
        ordering = ['-tahun_lulus']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.jenjang} {self.bidang_ilmu}"


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

    # Upload sertifikat langsung
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

    # Upload langsung untuk dokumen kecil
    file_dokumen = models.FileField(
        upload_to=upload_dokumen,
        validators=[validate_file],
        blank=True, null=True
    )
    # Link Drive untuk dokumen besar
    link_dokumen = models.URLField(blank=True, null=True)

    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Dokumen Lain'
        verbose_name_plural = 'Dokumen Lain'
        ordering = ['-tgl_input']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.nama_dokumen}"

class BKD(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='bkd_set'
    )
    semester = models.CharField(
        max_length=10,
        choices=[('Ganjil', 'Ganjil'), ('Genap', 'Genap')]
    )
    tahun_akademik = models.CharField(max_length=10)

    # Hybrid — upload atau link
    file_bkd = models.FileField(
        upload_to=upload_bkd,
        validators=[validate_file],
        blank=True, null=True,
        help_text='Upload file PDF BKD (max 5MB)'
    )
    link_bkd = models.URLField(
        blank=True, null=True,
        help_text='Atau isi link Google Drive jika file besar'
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
    def label_status(self):
        if self.file_bkd or self.link_bkd:
            return 'Terupload'
        return 'Belum Upload'