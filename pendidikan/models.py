"""Kategori SISTER 'Pelaks. pendidikan'. Field mengikuti Pengajaran.docx
(A/B/C detail lengkap dari dokumen) + field standar untuk D-G (diusulkan,
dikonfirmasi user). Hanya item yang sering dilakukan dosen Unisan yang
dibangun -- Visiting Scientist, Detasering, Pembimbing Dosen (PA) sengaja
tidak dibuatkan menu.

Mata Kuliah & Mahasiswa dipilih dari referensi SIMDA (simda_dosen.MataKuliahPublik/
MahasiswaPublik, database 'simda') -- karena model di app ini hidup di
database lokal SIKD (default), FK lintas-database tidak didukung Django,
jadi disimpan sebagai id polos + snapshot field (nim/nama/kode_mk/dst) supaya
riwayat tetap terbaca walau data rujukan di SIMDA berubah/terhapus.
"""
from django.db import models
from accounts.models import User

SEMESTER_CHOICES = [
    ('Ganjil', 'Ganjil'),
    ('Genap', 'Genap'),
    ('Keduanya', 'Keduanya'),
]

TINGKAT_CHOICES = [
    ('L', 'Lokal'), ('R', 'Regional'), ('N', 'Nasional'), ('I', 'Internasional'),
]


class Pengajaran(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pengajaran_set')
    kode_prodi = models.CharField(max_length=10, blank=True, null=True)
    kode_fakultas = models.CharField(max_length=10, blank=True, null=True)

    prodi_mengajar_kode = models.CharField(
        max_length=10, verbose_name='Program Studi Mengajar',
        help_text='Bisa beda dari prodi induk dosen (khususnya dosen MKDU lintas prodi)'
    )
    no_sk_penugasan = models.CharField(max_length=100, blank=True, null=True)
    tanggal_sk_penugasan = models.DateField(blank=True, null=True)

    mata_kuliah_id = models.IntegerField(help_text='id ke simda_dosen.MataKuliahPublik')
    kode_mk = models.CharField(max_length=20)
    nama_mk = models.CharField(max_length=200)
    jenis_mk = models.CharField(max_length=20, blank=True, null=True)
    sks_total = models.IntegerField(blank=True, null=True)

    nama_kelas = models.CharField(max_length=50, blank=True, null=True)
    jumlah_pertemuan = models.IntegerField(blank=True, null=True)
    jumlah_mahasiswa = models.IntegerField(default=0)

    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES, blank=True, null=True)
    tahun_akademik = models.CharField(max_length=10)
    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Pengajaran'
        verbose_name_plural = 'Pengajaran'
        ordering = ['-tahun_akademik', 'semester']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.nama_mk} ({self.nama_kelas})"

    @property
    def periode(self):
        return f"{self.semester} {self.tahun_akademik}" if self.semester else self.tahun_akademik


class BimbinganMahasiswa(models.Model):
    JENIS_BIMBINGAN = [
        ('skripsi', 'Skripsi/Tugas Akhir'),
        ('tesis', 'Tesis'),
        ('disertasi', 'Disertasi'),
    ]
    KATEGORI = [
        ('utama', 'Pembimbing Utama'),
        ('pendamping', 'Pembimbing Pendamping'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bimbingan_set')
    kode_prodi = models.CharField(max_length=10, blank=True, null=True)
    kode_fakultas = models.CharField(max_length=10, blank=True, null=True)

    prodi_mahasiswa_kode = models.CharField(
        max_length=10, verbose_name='Program Studi Mahasiswa',
        help_text='Bisa lintas prodi, mis. dosen Manajemen S1 membimbing di Manajemen S2'
    )
    jenis_bimbingan = models.CharField(max_length=15, choices=JENIS_BIMBINGAN)
    no_sk_penugasan = models.CharField(max_length=100, blank=True, null=True)
    tanggal_sk_penugasan = models.DateField(blank=True, null=True)

    mahasiswa_id = models.IntegerField(help_text='id ke simda_dosen.MahasiswaPublik')
    nim = models.CharField(max_length=20)
    nama_mahasiswa = models.CharField(max_length=150)

    judul_bimbingan = models.TextField(verbose_name='Judul Bimbingan (Tugas Akhir)')
    kategori = models.CharField(max_length=15, choices=KATEGORI)

    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES, blank=True, null=True)
    tahun_akademik = models.CharField(max_length=10)
    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Bimbingan Mahasiswa'
        verbose_name_plural = 'Bimbingan Mahasiswa'
        ordering = ['-tahun_akademik', 'semester']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.nama_mahasiswa} ({self.get_jenis_bimbingan_display()})"

    @property
    def periode(self):
        return f"{self.semester} {self.tahun_akademik}" if self.semester else self.tahun_akademik


class PengujianMahasiswa(models.Model):
    KATEGORI = [
        ('ketua', 'Ketua Penguji'),
        ('anggota1', 'Anggota Penguji 1'),
        ('anggota2', 'Anggota Penguji 2'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pengujian_set')
    kode_prodi = models.CharField(max_length=10, blank=True, null=True)
    kode_fakultas = models.CharField(max_length=10, blank=True, null=True)

    prodi_mahasiswa_kode = models.CharField(max_length=10, verbose_name='Program Studi Mahasiswa')
    no_sk_penugasan = models.CharField(max_length=100, blank=True, null=True)
    tanggal_sk_penugasan = models.DateField(blank=True, null=True)

    mahasiswa_id = models.IntegerField(help_text='id ke simda_dosen.MahasiswaPublik')
    nim = models.CharField(max_length=20)
    nama_mahasiswa = models.CharField(max_length=150)

    judul_pengujian = models.TextField(verbose_name='Judul Pengujian (Tugas Akhir)')
    kategori = models.CharField(max_length=15, choices=KATEGORI)

    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES, blank=True, null=True)
    tahun_akademik = models.CharField(max_length=10)
    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Pengujian Mahasiswa'
        verbose_name_plural = 'Pengujian Mahasiswa'
        ordering = ['-tahun_akademik', 'semester']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.nama_mahasiswa} ({self.get_kategori_display()})"

    @property
    def periode(self):
        return f"{self.semester} {self.tahun_akademik}" if self.semester else self.tahun_akademik


class BahanAjar(models.Model):
    JENIS_BAHAN_AJAR = [
        ('buku_ajar', 'Buku Ajar'),
        ('modul', 'Modul'),
        ('diktat', 'Diktat'),
        ('petunjuk_praktikum', 'Petunjuk Praktikum'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bahan_ajar_set')
    kode_prodi = models.CharField(max_length=10, blank=True, null=True)
    kode_fakultas = models.CharField(max_length=10, blank=True, null=True)

    jenis_bahan_ajar = models.CharField(max_length=20, choices=JENIS_BAHAN_AJAR)
    judul = models.CharField(max_length=250)
    isbn = models.CharField(max_length=30, blank=True, null=True)
    penerbit = models.CharField(max_length=150, blank=True, null=True)
    tahun_terbit = models.IntegerField()
    jumlah_halaman = models.IntegerField(blank=True, null=True)

    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES, blank=True, null=True)
    tahun_akademik = models.CharField(max_length=10, blank=True, null=True)
    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Bahan Ajar'
        verbose_name_plural = 'Bahan Ajar'
        ordering = ['-tahun_terbit']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.judul}"

    @property
    def periode(self):
        return f"{self.semester} {self.tahun_akademik}" if self.semester else str(self.tahun_terbit)


class PenulisBahanAjar(models.Model):
    """Penulis Bahan Ajar bisa lebih dari satu (dosen/mahasiswa/lain), sesuai
    form SISTER asli. dosen_id/mahasiswa_id merujuk ke simda_dosen.DataDosen/
    MahasiswaPublik (dosen internal Unisan saja, dicari lewat AJAX) -- untuk
    jenis_penulis='lain' nama diketik manual. Nama & NIDN/NIM disimpan sebagai
    snapshot supaya riwayat tetap terbaca walau data rujukan berubah."""
    JENIS_PENULIS = [
        ('dosen', 'Dosen'),
        ('mahasiswa', 'Mahasiswa'),
        ('lain', 'Lainnya'),
    ]
    PERAN = [
        ('penulis', 'Penulis'),
        ('editor', 'Editor'),
        ('penerjemah', 'Penerjemah'),
        ('penemu_inventor', 'Penemu/Inventor'),
    ]

    bahan_ajar = models.ForeignKey(BahanAjar, on_delete=models.CASCADE, related_name='penulis_set')
    jenis_penulis = models.CharField(max_length=10, choices=JENIS_PENULIS)

    dosen_id = models.IntegerField(null=True, blank=True, help_text='id ke simda_dosen.DataDosen, diisi kalau jenis_penulis=dosen')
    mahasiswa_id = models.IntegerField(null=True, blank=True, help_text='id ke simda_dosen.MahasiswaPublik, diisi kalau jenis_penulis=mahasiswa')

    nama = models.CharField(max_length=150)
    nidn_nim = models.CharField(max_length=20, blank=True, verbose_name='NIDN/NIM')
    urutan = models.IntegerField(default=1)
    afiliasi = models.CharField(max_length=200, blank=True)
    peran = models.CharField(max_length=20, choices=PERAN, default='penulis')

    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Penulis Bahan Ajar'
        verbose_name_plural = 'Penulis Bahan Ajar'
        ordering = ['urutan']

    def __str__(self):
        return f"{self.bahan_ajar.judul[:40]} - {self.nama}"


class PembinaanMahasiswa(models.Model):
    JENIS_KEGIATAN = [
        ('penasehat_akademik', 'Penasehat Akademik'),
        ('pembina_ukm', 'Pembina UKM'),
        ('pembina_ormawa', 'Pembina Ormawa'),
        ('pembina_kompetisi', 'Pembina Kompetisi Mahasiswa'),
        ('lainnya', 'Lainnya'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pembinaan_mahasiswa_set')
    kode_prodi = models.CharField(max_length=10, blank=True, null=True)
    kode_fakultas = models.CharField(max_length=10, blank=True, null=True)

    jenis_kegiatan = models.CharField(max_length=20, choices=JENIS_KEGIATAN)
    nama_kegiatan = models.CharField(max_length=200)
    tingkat = models.CharField(max_length=5, choices=TINGKAT_CHOICES, blank=True, null=True)
    tahun = models.IntegerField()

    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES, blank=True, null=True)
    tahun_akademik = models.CharField(max_length=10, blank=True, null=True)
    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Pembinaan Mahasiswa'
        verbose_name_plural = 'Pembinaan Mahasiswa'
        ordering = ['-tahun']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.nama_kegiatan}"

    @property
    def periode(self):
        return f"{self.semester} {self.tahun_akademik}" if self.semester else str(self.tahun)


class OrasiIlmiah(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orasi_ilmiah_set')
    kode_prodi = models.CharField(max_length=10, blank=True, null=True)
    kode_fakultas = models.CharField(max_length=10, blank=True, null=True)

    judul_orasi = models.CharField(max_length=250)
    penyelenggara = models.CharField(max_length=150, blank=True, null=True)
    tanggal = models.DateField()
    tingkat = models.CharField(max_length=5, choices=TINGKAT_CHOICES, blank=True, null=True)

    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES, blank=True, null=True)
    tahun_akademik = models.CharField(max_length=10, blank=True, null=True)
    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Orasi Ilmiah'
        verbose_name_plural = 'Orasi Ilmiah'
        ordering = ['-tanggal']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.judul_orasi}"

    @property
    def periode(self):
        return f"{self.semester} {self.tahun_akademik}" if self.semester else str(self.tanggal.year)


class TugasTambahan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tugas_tambahan_set')
    kode_prodi = models.CharField(max_length=10, blank=True, null=True)
    kode_fakultas = models.CharField(max_length=10, blank=True, null=True)

    jabatan_tambahan = models.CharField(max_length=200, help_text='Contoh: Kaprodi Manajemen, Kepala LPPM')
    no_sk = models.CharField(max_length=100, blank=True, null=True)
    tanggal_sk = models.DateField(blank=True, null=True)
    tanggal_mulai = models.DateField()
    tanggal_selesai = models.DateField(blank=True, null=True, help_text='Kosongkan jika masih menjabat')

    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES, blank=True, null=True)
    tahun_akademik = models.CharField(max_length=10, blank=True, null=True)
    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Tugas Tambahan'
        verbose_name_plural = 'Tugas Tambahan'
        ordering = ['-tanggal_mulai']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.jabatan_tambahan}"

    @property
    def periode(self):
        return f"{self.semester} {self.tahun_akademik}" if self.semester else str(self.tanggal_mulai.year)

    @property
    def masih_menjabat(self):
        return self.tanggal_selesai is None
