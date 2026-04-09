from django.db import models

class Fakultas(models.Model):
    kode_fakultas = models.CharField(max_length=10, unique=True)
    nama_fakultas = models.CharField(max_length=100)
    nama_dekan = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(
        max_length=10,
        choices=[('aktif', 'Aktif'), ('nonaktif', 'Nonaktif')],
        default='aktif'
    )

    class Meta:
        verbose_name = 'Fakultas'
        verbose_name_plural = 'Fakultas'
        ordering = ['kode_fakultas']

    def __str__(self):
        return f"{self.kode_fakultas} - {self.nama_fakultas}"


class Prodi(models.Model):
    kode_prodi = models.CharField(max_length=10, unique=True)
    nama_prodi = models.CharField(max_length=100)
    fakultas = models.ForeignKey(
        Fakultas,
        on_delete=models.CASCADE,
        related_name='prodi_set'
    )
    nama_kaprodi = models.CharField(max_length=100, blank=True, null=True)
    jenjang = models.CharField(
        max_length=5,
        choices=[('S1', 'S1'), ('S2', 'S2'), ('S3', 'S3'), ('D3', 'D3'), ('D4', 'D4')],
        default='S1'
    )
    status = models.CharField(
        max_length=10,
        choices=[('aktif', 'Aktif'), ('nonaktif', 'Nonaktif')],
        default='aktif'
    )

    class Meta:
        verbose_name = 'Program Studi'
        verbose_name_plural = 'Program Studi'
        ordering = ['fakultas__kode_fakultas', 'kode_prodi']

    def __str__(self):
        return f"{self.kode_prodi} - {self.nama_prodi}"


class TahunAkademik(models.Model):
    tahun_akademik = models.CharField(max_length=10, unique=True)
    keterangan = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(
        max_length=10,
        choices=[('aktif', 'Aktif'), ('nonaktif', 'Nonaktif')],
        default='aktif'
    )
    urutan = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Tahun Akademik'
        verbose_name_plural = 'Tahun Akademik'
        ordering = ['-urutan']

    def __str__(self):
        return self.tahun_akademik


class Pengaturan(models.Model):
    status_input = models.CharField(
        max_length=10,
        choices=[('buka', 'Buka'), ('kunci', 'Kunci')],
        default='buka'
    )
    deadline = models.DateField(blank=True, null=True)
    ts_label = models.CharField(max_length=10, default='TS')
    ts_tahun = models.CharField(max_length=10, default='2024-2025')
    ts1_label = models.CharField(max_length=10, default='TS-1')
    ts1_tahun = models.CharField(max_length=10, default='2023-2024')
    ts2_label = models.CharField(max_length=10, default='TS-2')
    ts2_tahun = models.CharField(max_length=10, default='2022-2023')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Pengaturan'
        verbose_name_plural = 'Pengaturan'

    def __str__(self):
        return f"Pengaturan Aktif - {self.ts_tahun}"