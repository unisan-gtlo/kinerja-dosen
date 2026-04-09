from django.db import models
from accounts.models import User

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
    tahun_akademik = models.CharField(max_length=10)
    pendanaan = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )
    # Link Drive — laporan penelitian biasanya besar
    link_bukti = models.URLField(blank=True, null=True)

    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Penelitian'
        verbose_name_plural = 'Penelitian'
        ordering = ['-tahun_akademik']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.judul[:50]}"


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
    tahun_akademik = models.CharField(max_length=10)
    # Link ke jurnal online
    link_bukti = models.URLField(blank=True, null=True)

    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Publikasi'
        verbose_name_plural = 'Publikasi'
        ordering = ['-tahun_akademik']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.judul[:50]}"


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
    tahun_akademik = models.CharField(max_length=10)
    pendanaan = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )
    # Link Drive — laporan PKM biasanya besar
    link_bukti = models.URLField(blank=True, null=True)

    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Pengabdian Masyarakat'
        verbose_name_plural = 'Pengabdian Masyarakat'
        ordering = ['-tahun_akademik']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.judul[:50]}"


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
    tahun_akademik = models.CharField(max_length=10)
    # Link ke sertifikat HKI — bisa upload atau link
    link_bukti = models.URLField(blank=True, null=True)

    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'HKI'
        verbose_name_plural = 'HKI'
        ordering = ['-tahun_akademik']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.judul[:50]}"