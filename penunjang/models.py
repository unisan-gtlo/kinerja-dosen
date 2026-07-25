"""Kategori SISTER 'Penunjang' -- menu top-level tersendiri (sejajar
Pelaks. Pendidikan/Penelitian/Pengabdian), bukan bagian dari menu lain.
Field mengikuti Penunjang.docx (screenshot form SISTER asli): Anggota
Profesi, Penghargaan, Penunjang Lain.

Penghargaan & PenunjangLain menggantikan kinerja.Penghargaan/
KegiatanPenunjang (model lama, field-nya beda taksonomi total dari
SISTER asli) -- related_name FK sengaja dipertahankan 'penghargaan_set'/
'penunjang_set' supaya pemanggil lama di dashboard/laporan tidak perlu
diubah, sama pola dengan app penelitian/pengabdian.

Kategori Kegiatan di form "Penunjang Lain" punya banyak leaf item nested
yang tidak semuanya terlihat jelas di screenshot referensi -- sengaja
dibuat CharField bebas di sini, beda dengan Jenis Kegiatan/Tingkat yang
pilihannya lengkap terlihat sehingga pakai choices tetap.

Anggota Kegiatan (Dosen) di Penunjang Lain HANYA dosen (beda dari
AnggotaPenelitian/AnggotaPengabdian yang juga punya opsi mahasiswa/
kolaborator eksternal) -- sesuai screenshot form asli cuma ada kolom
Perguruan Tinggi + Nama Dosen + Peran.
"""
from django.db import models
from accounts.models import User

SEMESTER_CHOICES = [
    ('Ganjil', 'Ganjil'),
    ('Genap', 'Genap'),
    ('Keduanya', 'Keduanya'),
]


class AnggotaProfesi(models.Model):
    KATEGORI_KEGIATAN = [
        ('org_internasional_pengurus', 'Tingkat internasional sebagai pengurus'),
        ('org_internasional_anggota_permintaan', 'Tingkat internasional sebagai anggota atas permintaan'),
        ('org_internasional_anggota', 'Tingkat internasional sebagai anggota'),
        ('org_nasional_pengurus', 'Tingkat nasional sebagai pengurus'),
        ('org_nasional_anggota_permintaan', 'Tingkat nasional sebagai anggota atas permintaan'),
        ('org_nasional_anggota', 'Tingkat nasional sebagai anggota'),
        ('dosen_nasional_pengurus_aktif', 'Tingkat nasional sebagai pengurus aktif'),
        ('dosen_nasional_anggota_aktif', 'Tingkat nasional sebagai anggota aktif'),
        ('dosen_daerah_pengurus_aktif', 'Tingkat nasional provinsi/kabupaten/kota sebagai pengurus aktif'),
        ('dosen_daerah_anggota_aktif', 'Tingkat nasional provinsi/kabupaten/kota sebagai anggota aktif'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='anggota_profesi_set')
    kode_prodi = models.CharField(max_length=10, blank=True, null=True)
    kode_fakultas = models.CharField(max_length=10, blank=True, null=True)

    kategori_kegiatan = models.CharField(max_length=40, choices=KATEGORI_KEGIATAN)
    nama_organisasi = models.CharField(max_length=200)
    peran = models.CharField(max_length=150)
    mulai_keanggotaan = models.DateField()
    selesai_keanggotaan = models.DateField(null=True, blank=True)
    instansi_profesi = models.CharField(max_length=200, blank=True)

    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES, blank=True, null=True)
    tahun_akademik = models.CharField(max_length=10, blank=True, null=True)
    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Anggota Profesi'
        verbose_name_plural = 'Anggota Profesi'
        ordering = ['-mulai_keanggotaan']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.nama_organisasi}"

    @property
    def periode(self):
        return f"{self.semester} {self.tahun_akademik}" if self.semester else str(self.mulai_keanggotaan.year)


class Penghargaan(models.Model):
    KATEGORI_KEGIATAN = [
        ('satyalancana_30', 'Penghargaan/tanda jasa Satyalancana Karya Satya 30 tahun'),
        ('satyalancana_20', 'Penghargaan/tanda jasa Satyalancana Karya Satya 20 tahun'),
        ('satyalancana_10', 'Penghargaan/tanda jasa Satyalancana Karya Satya 10 tahun'),
        ('lainnya_internasional', 'Penghargaan lainnya tingkat internasional'),
        ('lainnya_nasional', 'Penghargaan lainnya tingkat nasional'),
        ('lainnya_provinsi_lokal', 'Penghargaan lainnya tingkat provinsi/lokal'),
        ('prestasi_internasional', 'Prestasi olahraga/humaniora tingkat internasional'),
        ('prestasi_nasional', 'Prestasi olahraga/humaniora tingkat nasional'),
        ('prestasi_daerah_lokal', 'Prestasi olahraga/humaniora tingkat daerah/lokal'),
    ]
    TINGKAT_PENGHARGAAN = [
        ('sekolah', 'Sekolah'),
        ('kecamatan', 'Kecamatan'),
        ('kabkota', 'Kab/kota'),
        ('propinsi', 'Propinsi'),
        ('nasional', 'Nasional'),
        ('internasional', 'Internasional'),
        ('lainnya', 'Lainnya'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='penghargaan_set')
    kode_prodi = models.CharField(max_length=10, blank=True, null=True)
    kode_fakultas = models.CharField(max_length=10, blank=True, null=True)

    kategori_kegiatan = models.CharField(max_length=30, choices=KATEGORI_KEGIATAN)
    tingkat_penghargaan = models.CharField(max_length=20, choices=TINGKAT_PENGHARGAAN)
    jenis_penghargaan = models.CharField(max_length=150, blank=True)
    nama_penghargaan = models.CharField(max_length=200)
    tahun = models.IntegerField()
    instansi_pemberi = models.CharField(max_length=200)

    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES, blank=True, null=True)
    tahun_akademik = models.CharField(max_length=10, blank=True, null=True)
    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Penghargaan'
        verbose_name_plural = 'Penghargaan'
        ordering = ['-tahun']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.nama_penghargaan}"

    @property
    def periode(self):
        return f"{self.semester} {self.tahun_akademik}" if self.semester else str(self.tahun)


class PenunjangLain(models.Model):
    JENIS_KEGIATAN = [
        ('panitia_pt', 'Panitia/badan pada perguruan tinggi'),
        ('panitia_lembaga_pemerintah', 'Panitia/badan pada lembaga pemerintah'),
        ('delegasi_nasional', 'Delegasi nasional ke pertemuan internasional'),
        ('panitia_pertemuan_ilmiah', 'Panitia pada pertemuan ilmiah'),
        ('tim_penilai_jabatan_akademik', 'Tim penilai jabatan akademik dosen'),
        ('sebagai_anggota', 'Sebagai anggota'),
        ('panitia_lainnya', 'Panitia lainnya'),
    ]
    TINGKAT = [
        ('lokal', 'Lokal'),
        ('daerah', 'Daerah'),
        ('nasional', 'Nasional'),
        ('internasional', 'Internasional'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='penunjang_set')
    kode_prodi = models.CharField(max_length=10, blank=True, null=True)
    kode_fakultas = models.CharField(max_length=10, blank=True, null=True)

    kategori_kegiatan = models.CharField(max_length=200, blank=True)
    nama_kegiatan = models.CharField(max_length=200)
    jenis_kegiatan = models.CharField(max_length=30, choices=JENIS_KEGIATAN)
    instansi = models.CharField(max_length=200)
    tingkat = models.CharField(max_length=15, choices=TINGKAT)
    no_sk_penugasan = models.CharField(max_length=100, blank=True)
    tanggal_mulai = models.DateField()
    tanggal_selesai = models.DateField(null=True, blank=True)

    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES, blank=True, null=True)
    tahun_akademik = models.CharField(max_length=10, blank=True, null=True)
    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Penunjang Lain'
        verbose_name_plural = 'Penunjang Lain'
        ordering = ['-tanggal_mulai']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.nama_kegiatan[:50]}"

    @property
    def periode(self):
        return f"{self.semester} {self.tahun_akademik}" if self.semester else str(self.tanggal_mulai.year)


class AnggotaPenunjangLain(models.Model):
    """Anggota Kegiatan (Dosen) di Penunjang Lain -- HANYA dosen, beda
    dari AnggotaPenelitian/AnggotaPengabdian yang juga punya opsi
    mahasiswa/kolaborator eksternal (tidak ada di form SISTER untuk
    Penunjang Lain)."""
    penunjang_lain = models.ForeignKey(PenunjangLain, on_delete=models.CASCADE, related_name='anggota_set')

    dosen_id = models.IntegerField(help_text='id ke simda_dosen.DataDosen')
    nama = models.CharField(max_length=150)
    nidn = models.CharField(max_length=20, blank=True, verbose_name='NIDN')
    perguruan_tinggi = models.CharField(max_length=200, blank=True)
    peran = models.CharField(max_length=150, blank=True)

    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Anggota Penunjang Lain'
        verbose_name_plural = 'Anggota Penunjang Lain'
        ordering = ['id']

    def __str__(self):
        return f"{self.penunjang_lain.nama_kegiatan[:40]} - {self.nama}"
