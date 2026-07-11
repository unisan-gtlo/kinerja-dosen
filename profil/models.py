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


# Model Sertifikat lama diganti Sertifikasi (di bawah, mengikuti spek SISTER:
# Kompetensi.docx) -- tapi upload_sertifikat TIDAK dihapus karena migration
# lama (0001/0002) merujuknya by-reference.

class Sertifikasi(models.Model):
    """Kategori Kompetensi > Sertifikasi. Field & alur mengikuti SISTER
    (Kompetensi.docx): Sertifikasi Dosen (Serdos) butuh validasi kaprodi/dekan,
    Sertifikasi Kompetensi/Profesi langsung aktif tanpa validasi."""
    JENIS_SERTIFIKASI = [
        ('serdos', 'Sertifikasi Dosen'),
        ('kompetensi', 'Sertifikasi Kompetensi'),
        ('profesi', 'Sertifikasi Profesi'),
    ]
    STATUS_VALIDASI = [
        ('menunggu', 'Menunggu Validasi'),
        ('disetujui', 'Disetujui'),
        ('ditolak', 'Ditolak'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='sertifikasi_set'
    )
    kode_prodi = models.CharField(max_length=10, blank=True, null=True)
    kode_fakultas = models.CharField(max_length=10, blank=True, null=True)
    jenis_sertifikasi = models.CharField(max_length=15, choices=JENIS_SERTIFIKASI)
    bidang_studi = models.CharField(max_length=150)
    lembaga_sertifikasi = models.CharField(
        max_length=150, blank=True, null=True,
        help_text='Diisi untuk Sertifikasi Kompetensi/Profesi'
    )
    no_registrasi_pendidik = models.CharField(max_length=50, blank=True, null=True)
    no_peserta = models.CharField(
        max_length=50, blank=True, null=True,
        help_text='Diisi untuk Sertifikasi Dosen (Serdos)'
    )
    no_sk_sertifikasi = models.CharField(max_length=100)
    tahun_sertifikasi = models.IntegerField()
    tmt_sertifikasi = models.DateField(
        blank=True, null=True, verbose_name='TMT Sertifikasi',
        help_text='Terhitung Mulai Tanggal -- diisi untuk Kompetensi/Profesi'
    )
    tst_sertifikasi = models.DateField(
        blank=True, null=True, verbose_name='TST Sertifikasi',
        help_text='Tanggal Selesai Tugas -- diisi untuk Kompetensi/Profesi'
    )
    status_validasi = models.CharField(
        max_length=15, choices=STATUS_VALIDASI, default='menunggu'
    )
    semester = models.CharField(
        max_length=10,
        choices=[('Ganjil', 'Ganjil'), ('Genap', 'Genap'), ('Keduanya', 'Keduanya')],
        blank=True, null=True
    )
    tahun_akademik = models.CharField(max_length=10, blank=True, null=True)
    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    # Serdos butuh validasi kaprodi/dekan/rektorat -- dosen pemilik tidak
    # bisa validasi sertifikasinya sendiri. Sama pola dengan RiwayatBKD.
    ROLE_BOLEH_VALIDASI = ['admin', 'kaprodi', 'sekprodi', 'dekan', 'wadek', 'rektorat']

    class Meta:
        verbose_name = 'Sertifikasi'
        verbose_name_plural = 'Sertifikasi'
        ordering = ['-tahun_sertifikasi']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_jenis_sertifikasi_display()} ({self.bidang_studi})"

    @property
    def periode(self):
        if self.semester:
            return f"{self.semester} {self.tahun_akademik}"
        return str(self.tahun_sertifikasi)


class TesKompetensi(models.Model):
    """Kategori Kompetensi > Tes (IELTS/TOEFL/TOEIC/TKBI/TKDA dll)."""
    JENIS_TES = [
        ('ielts', 'IELTS'),
        ('toefl_ibt', 'TOEFL iBT'),
        ('toefl_itp', 'TOEFL ITP'),
        ('toeic', 'TOEIC'),
        ('tkbi', 'TKBI'),
        ('tkda', 'TKDA'),
        ('lainnya', 'Lainnya'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='tes_set'
    )
    kode_prodi = models.CharField(max_length=10, blank=True, null=True)
    kode_fakultas = models.CharField(max_length=10, blank=True, null=True)
    jenis_tes = models.CharField(max_length=15, choices=JENIS_TES)
    nama_tes = models.CharField(max_length=150)
    penyelenggara = models.CharField(max_length=150)
    tanggal_tes = models.DateField()
    tahun = models.IntegerField()
    skor_tes = models.DecimalField(max_digits=7, decimal_places=2)
    semester = models.CharField(
        max_length=10,
        choices=[('Ganjil', 'Ganjil'), ('Genap', 'Genap'), ('Keduanya', 'Keduanya')],
        blank=True, null=True
    )
    tahun_akademik = models.CharField(max_length=10, blank=True, null=True)
    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Tes Kompetensi'
        verbose_name_plural = 'Tes Kompetensi'
        ordering = ['-tahun']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_jenis_tes_display()} ({self.skor_tes})"

    @property
    def periode(self):
        if self.semester:
            return f"{self.semester} {self.tahun_akademik}"
        return str(self.tahun)


def upload_diklat(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f'diklat/{instance.user.username}/{filename}'


class Diklat(models.Model):
    """Kategori Kualifikasi > Diklat, field mengikuti form SISTER (Menu Diklat.docx)."""
    JENIS_DIKLAT = [
        ('pelatihan_profesional', 'Pelatihan Profesional'),
        ('lemhanas', 'Lemhanas'),
        ('diklat_prajabatan', 'Diklat Prajabatan'),
        ('diklat_kepemimpinan', 'Diklat Kepemimpinan'),
        ('academic_exchange', 'Academic Exchange'),
        ('lainnya', 'Lainnya'),
    ]
    TINGKATAN = [
        ('Lokal', 'Lokal'),
        ('Regional', 'Regional'),
        ('Nasional', 'Nasional'),
        ('Internasional', 'Internasional'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='diklat_set'
    )
    kode_prodi = models.CharField(max_length=10, blank=True, null=True)
    kode_fakultas = models.CharField(max_length=10, blank=True, null=True)
    jenis_diklat = models.CharField(max_length=25, choices=JENIS_DIKLAT)
    nama_diklat = models.CharField(max_length=200)
    penyelenggara = models.CharField(max_length=200)
    peran = models.CharField(max_length=100, blank=True, null=True)
    tingkatan = models.CharField(max_length=15, choices=TINGKATAN)
    jumlah_jam = models.IntegerField(blank=True, null=True)
    no_sertifikat = models.CharField(max_length=100)
    tanggal_sertifikat = models.DateField()
    tahun_penyelenggaraan = models.IntegerField()
    tempat = models.CharField(max_length=150, blank=True, null=True)
    tanggal_mulai = models.DateField()
    tanggal_selesai = models.DateField()
    no_sk_penugasan = models.CharField(max_length=100, blank=True, null=True)
    tanggal_sk_penugasan = models.DateField(blank=True, null=True)
    semester = models.CharField(
        max_length=10,
        choices=[('Ganjil', 'Ganjil'), ('Genap', 'Genap'), ('Keduanya', 'Keduanya')],
        blank=True, null=True
    )
    tahun_akademik = models.CharField(max_length=10, blank=True, null=True)
    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Diklat'
        verbose_name_plural = 'Diklat'
        ordering = ['-tahun_penyelenggaraan']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.nama_diklat}"

    @property
    def periode(self):
        if self.semester:
            return f"{self.semester} {self.tahun_akademik}"
        return str(self.tahun_penyelenggaraan)


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
