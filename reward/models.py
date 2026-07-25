"""Kategori SISTER 'Reward' -- menu top-level tersendiri (sejajar
Pelaks. Pendidikan/Penelitian/Pengabdian/Penunjang). Field mengikuti
Reward.docx (screenshot form SISTER asli): Beasiswa, Kesejahteraan,
Tunjangan.

Beda dari menu SISTER lain yang sudah dibangun -- form aslinya TIDAK
punya field Semester/Tahun Akademik maupun Kategori Kegiatan nested-tree
atau fitur anggota/co-author, jadi 3 model di sini sengaja dibuat flat
tanpa field-field itu.
"""
from django.db import models
from accounts.models import User


class Beasiswa(models.Model):
    JENIS_BEASISWA = [
        ('prestasi', 'Prestasi'),
        ('kemiskinan', 'Kemiskinan'),
        ('pendidikan', 'Pendidikan'),
        ('unggulan', 'Unggulan'),
        ('ikatan_dinas', 'Ikatan Dinas'),
        ('peningkatan_karir', 'Peningkatan Karir'),
        ('lainnya', 'Lainnya'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='beasiswa_set')
    kode_prodi = models.CharField(max_length=10, blank=True, null=True)
    kode_fakultas = models.CharField(max_length=10, blank=True, null=True)

    jenis_beasiswa = models.CharField(max_length=20, choices=JENIS_BEASISWA)
    nama_beasiswa = models.CharField(max_length=200)
    tahun_mulai = models.IntegerField()
    tahun_selesai = models.IntegerField(null=True, blank=True)
    masih_terima = models.BooleanField(default=True)

    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Beasiswa'
        verbose_name_plural = 'Beasiswa'
        ordering = ['-tahun_mulai']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.nama_beasiswa}"

    @property
    def periode(self):
        return str(self.tahun_mulai)


class Kesejahteraan(models.Model):
    JENIS_KESEJAHTERAAN = [
        ('asuransi_kesejahteraan', 'Asuransi Kesejahteraan'),
        ('dana_pensiun', 'Dana Pensiun'),
        ('jamkesmas', 'Jamkesmas'),
        ('jamsostek', 'Jamsostek'),
        ('lainnya', 'Lainnya'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='kesejahteraan_set')
    kode_prodi = models.CharField(max_length=10, blank=True, null=True)
    kode_fakultas = models.CharField(max_length=10, blank=True, null=True)

    jenis_kesejahteraan = models.CharField(max_length=30, choices=JENIS_KESEJAHTERAAN)
    layanan_kesejahteraan = models.CharField(max_length=200)
    penyelenggara = models.CharField(max_length=200)
    tahun_mulai = models.IntegerField()
    tahun_selesai = models.IntegerField(null=True, blank=True)

    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Kesejahteraan'
        verbose_name_plural = 'Kesejahteraan'
        ordering = ['-tahun_mulai']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.layanan_kesejahteraan}"

    @property
    def periode(self):
        return str(self.tahun_mulai)


class Tunjangan(models.Model):
    JENIS_TUNJANGAN = [
        ('tunjangan_anak', 'Tunjangan Anak'),
        ('tunjangan_istri_suami', 'Tunjangan Istri/Suami'),
        ('tunjangan_beras', 'Tunjangan Beras'),
        ('tunjangan_umum_pns', 'Tunjangan Umum PNS'),
        ('tunjangan_khusus_guru_dosen', 'Tunjangan Khusus Guru/Dosen'),
        ('tunjangan_medis', 'Tunjangan Medis'),
        ('tunjangan_pegawai_non_pns', 'Tunjangan Pegawai Non PNS'),
        ('tunjangan_hari_tua', 'Tunjangan Hari Tua'),
        ('bantuan_kualifikasi_akademik', 'Bantuan Peningkatan Kualifikasi Akademik'),
        ('tunjangan_guru_daerah_khusus', 'Tunjangan Guru Daerah Khusus'),
        ('tunjangan_fungsional_non_pns', 'Tunjangan Fungsional Non PNS'),
        ('tunjangan_pendidikan_layanan_khusus', 'Tunjangan Pendidikan Khusus & Layanan Khusus'),
        ('lainnya', 'Lainnya'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tunjangan_set')
    kode_prodi = models.CharField(max_length=10, blank=True, null=True)
    kode_fakultas = models.CharField(max_length=10, blank=True, null=True)

    jenis_tunjangan = models.CharField(max_length=40, choices=JENIS_TUNJANGAN)
    nama_tunjangan = models.CharField(max_length=200)
    instansi_pemberi_tunjangan = models.CharField(max_length=200, blank=True)
    sumber_dana = models.CharField(max_length=150, blank=True)
    tahun_mulai = models.IntegerField()
    tahun_selesai = models.IntegerField(null=True, blank=True)
    nominal = models.DecimalField(max_digits=15, decimal_places=2)

    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Tunjangan'
        verbose_name_plural = 'Tunjangan'
        ordering = ['-tahun_mulai']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.nama_tunjangan}"

    @property
    def periode(self):
        return str(self.tahun_mulai)
