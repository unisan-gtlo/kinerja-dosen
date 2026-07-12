"""Kategori SISTER 'Pelaks. Penelitian' -- Penelitian, Publikasi Karya,
Paten/HKI. Field mengikuti Penelitian.docx (screenshot form SISTER asli).

Beberapa dropdown di form asli (Afiliasi, Kelompok Bidang, Jenis SKIM,
Kategori Capaian, Aktivitas Litabmas) sengaja dibuat CharField bebas di
sini karena daftar pilihan lengkapnya tidak terlihat jelas di screenshot
referensi -- gampang diubah jadi choices tetap kalau daftarnya sudah pasti.

Anggota/Penulis Dosen & Mahasiswa dipilih dari referensi SIMDA (id polos +
snapshot nama, sama pola dengan simda_dosen.MahasiswaPublik/DataDosen dan
pendidikan.PenulisBahanAjar) -- lihat catatan di app pendidikan untuk alasan
tidak pakai FK lintas-database.
"""
from django.db import models
from accounts.models import User

SEMESTER_CHOICES = [
    ('Ganjil', 'Ganjil'),
    ('Genap', 'Genap'),
    ('Keduanya', 'Keduanya'),
]

PERAN_ANGGOTA_CHOICES = [
    ('ketua', 'Ketua'),
    ('anggota', 'Anggota'),
]

PERAN_PENULIS_CHOICES = [
    ('penulis_pertama', 'Penulis Pertama'),
    ('penulis_korespondensi', 'Penulis Korespondensi'),
    ('anggota_penulis', 'Anggota Penulis'),
]


class Penelitian(models.Model):
    KATEGORI_PELAKSANAAN = [
        ('ketua', 'Sebagai Ketua'),
        ('anggota', 'Sebagai Anggota'),
        ('tidak_dipublikasikan', 'Hasil Penelitian Tidak Dipublikasikan'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='penelitian_set')
    kode_prodi = models.CharField(max_length=10, blank=True, null=True)
    kode_fakultas = models.CharField(max_length=10, blank=True, null=True)

    kategori_pelaksanaan = models.CharField(max_length=25, choices=KATEGORI_PELAKSANAAN)
    judul_kegiatan = models.TextField()
    afiliasi = models.CharField(max_length=200, blank=True)
    kelompok_bidang = models.CharField(max_length=150, blank=True)
    litabmas_sebelumnya = models.CharField(max_length=200, blank=True, verbose_name='Litabmas Sebelumnya')
    jenis_skim = models.CharField(max_length=150, blank=True, verbose_name='Jenis SKIM')
    lokasi_kegiatan = models.CharField(max_length=200, blank=True)

    tahun_usulan = models.IntegerField()
    tahun_kegiatan = models.CharField(max_length=10, help_text='Contoh: 2025/2026')
    tahun_pelaksanaan = models.IntegerField()
    lama_kegiatan_tahun = models.IntegerField(default=1, verbose_name='Lama Kegiatan (Tahun)')
    tahun_pelaksanaan_ke = models.IntegerField(default=1)

    dana_dikti = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Dana dari Dikti (Rp)')
    dana_pt = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Dana dari Perguruan Tinggi (Rp)')
    dana_institusi_lain = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Dana dari Institusi Lain (Rp)')
    in_kind = models.CharField(max_length=200, blank=True, verbose_name='In Kind')

    no_sk_penugasan = models.CharField(max_length=100, blank=True)
    tanggal_sk_penugasan = models.DateField(null=True, blank=True)
    mitra_litabmas = models.CharField(max_length=200, blank=True)

    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES, blank=True, null=True)
    tahun_akademik = models.CharField(max_length=10, blank=True, null=True)
    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Penelitian'
        verbose_name_plural = 'Penelitian'
        ordering = ['-tahun_pelaksanaan']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.judul_kegiatan[:50]}"

    @property
    def total_dana(self):
        return (self.dana_dikti or 0) + (self.dana_pt or 0) + (self.dana_institusi_lain or 0)

    @property
    def periode(self):
        return f"{self.semester} {self.tahun_akademik}" if self.semester else self.tahun_kegiatan


class AnggotaPenelitian(models.Model):
    """Anggota Kegiatan (Dosen/Mahasiswa/Kolaborator Eksternal) di Penelitian.
    Berbeda dari Penulis (di bawah) -- tidak ada urutan/afiliasi/corresponding
    author, cuma Peran (Ketua/Anggota) + Status Aktif, sesuai form SISTER."""
    JENIS_ANGGOTA = [
        ('dosen', 'Dosen'),
        ('mahasiswa', 'Mahasiswa'),
        ('kolaborator_eksternal', 'Kolaborator Eksternal'),
    ]

    penelitian = models.ForeignKey(Penelitian, on_delete=models.CASCADE, related_name='anggota_set')
    jenis_anggota = models.CharField(max_length=25, choices=JENIS_ANGGOTA)

    dosen_id = models.IntegerField(null=True, blank=True, help_text='id ke simda_dosen.DataDosen')
    mahasiswa_id = models.IntegerField(null=True, blank=True, help_text='id ke simda_dosen.MahasiswaPublik')

    nama = models.CharField(max_length=150)
    nidn_nim = models.CharField(max_length=20, blank=True, verbose_name='NIDN/NIM')
    perguruan_tinggi = models.CharField(max_length=200, blank=True)
    peran = models.CharField(max_length=10, choices=PERAN_ANGGOTA_CHOICES, default='anggota')
    status_aktif = models.BooleanField(default=True)

    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Anggota Penelitian'
        verbose_name_plural = 'Anggota Penelitian'
        ordering = ['jenis_anggota', 'id']

    def __str__(self):
        return f"{self.penelitian.judul_kegiatan[:40]} - {self.nama}"


class PublikasiKarya(models.Model):
    JENIS_PUBLIKASI = [
        ('jurnal_nasional', 'Jurnal Nasional'),
        ('jurnal_nasional_terakreditasi', 'Jurnal Nasional Terakreditasi'),
        ('artikel_ilmiah', 'Artikel Ilmiah'),
        ('makalah_ilmiah', 'Makalah Ilmiah'),
        ('tulisan_ilmiah', 'Tulisan Ilmiah'),
        ('prosiding_seminar_nasional', 'Prosiding Seminar Nasional'),
        ('lainnya', 'Lainnya'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='publikasi_set')
    kode_prodi = models.CharField(max_length=10, blank=True, null=True)
    kode_fakultas = models.CharField(max_length=10, blank=True, null=True)

    jenis = models.CharField(max_length=30, choices=JENIS_PUBLIKASI)
    kategori_capaian = models.CharField(max_length=150, blank=True)
    aktivitas_litabmas = models.CharField(max_length=200, blank=True)
    judul_artikel = models.TextField()
    nama_seminar = models.CharField(max_length=200, blank=True)
    tanggal_terbit = models.DateField()
    penerbit_penyelenggara = models.CharField(max_length=200, blank=True)
    kota_penyelenggaraan = models.CharField(max_length=100, blank=True)
    apakah_seminar = models.BooleanField(default=False)
    apakah_prosiding = models.BooleanField(default=False)
    bahasa = models.CharField(max_length=50, blank=True)
    isbn = models.CharField(max_length=30, blank=True, verbose_name='ISBN')
    issn = models.CharField(max_length=30, blank=True, verbose_name='ISSN')
    e_issn = models.CharField(max_length=30, blank=True, verbose_name='e-ISSN')
    tautan_eksternal = models.URLField(blank=True)
    keterangan = models.TextField(blank=True, verbose_name='Keterangan/Petunjuk Akses')

    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES, blank=True, null=True)
    tahun_akademik = models.CharField(max_length=10, blank=True, null=True)
    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Publikasi Karya'
        verbose_name_plural = 'Publikasi Karya'
        ordering = ['-tanggal_terbit']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.judul_artikel[:50]}"

    @property
    def periode(self):
        return f"{self.semester} {self.tahun_akademik}" if self.semester else str(self.tanggal_terbit.year)


class PenulisPublikasiKarya(models.Model):
    JENIS_PENULIS = [
        ('dosen', 'Dosen'),
        ('mahasiswa', 'Mahasiswa'),
        ('lain', 'Lainnya'),
    ]

    publikasi = models.ForeignKey(PublikasiKarya, on_delete=models.CASCADE, related_name='penulis_set')
    jenis_penulis = models.CharField(max_length=10, choices=JENIS_PENULIS)

    dosen_id = models.IntegerField(null=True, blank=True)
    mahasiswa_id = models.IntegerField(null=True, blank=True)

    nama = models.CharField(max_length=150)
    nidn_nim = models.CharField(max_length=20, blank=True, verbose_name='NIDN/NIM')
    urutan = models.IntegerField(default=1)
    afiliasi = models.CharField(max_length=200, blank=True)
    peran = models.CharField(max_length=25, choices=PERAN_PENULIS_CHOICES, default='anggota_penulis')
    corresponding_author = models.BooleanField(default=False)

    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Penulis Publikasi Karya'
        verbose_name_plural = 'Penulis Publikasi Karya'
        ordering = ['urutan']

    def __str__(self):
        return f"{self.publikasi.judul_artikel[:40]} - {self.nama}"


class PatenHki(models.Model):
    JENIS_PATEN = [
        ('paten_nasional', 'Paten Nasional'),
        ('paten_internasional', 'Paten Internasional'),
        ('hak_cipta_nasional', 'Hak Cipta Nasional'),
        ('hak_cipta_internasional', 'Hak Cipta Internasional'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hki_set')
    kode_prodi = models.CharField(max_length=10, blank=True, null=True)
    kode_fakultas = models.CharField(max_length=10, blank=True, null=True)

    jenis = models.CharField(max_length=30, choices=JENIS_PATEN)
    kategori_capaian = models.CharField(max_length=150, blank=True)
    aktivitas_litabmas = models.CharField(max_length=200, blank=True)
    judul_karya = models.TextField(verbose_name='Judul Karya/Kegiatan')
    tanggal = models.DateField()
    penyelenggara = models.CharField(max_length=200, blank=True)
    tautan_eksternal = models.URLField(blank=True)
    keterangan = models.TextField(blank=True, verbose_name='Keterangan/Petunjuk Akses')

    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES, blank=True, null=True)
    tahun_akademik = models.CharField(max_length=10, blank=True, null=True)
    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Paten/HKI'
        verbose_name_plural = 'Paten/HKI'
        ordering = ['-tanggal']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.judul_karya[:50]}"

    @property
    def periode(self):
        return f"{self.semester} {self.tahun_akademik}" if self.semester else str(self.tanggal.year)


class PenulisPatenHki(models.Model):
    JENIS_PENULIS = [
        ('dosen', 'Dosen'),
        ('mahasiswa', 'Mahasiswa'),
        ('lain', 'Lainnya'),
    ]

    paten_hki = models.ForeignKey(PatenHki, on_delete=models.CASCADE, related_name='penulis_set')
    jenis_penulis = models.CharField(max_length=10, choices=JENIS_PENULIS)

    dosen_id = models.IntegerField(null=True, blank=True)
    mahasiswa_id = models.IntegerField(null=True, blank=True)

    nama = models.CharField(max_length=150)
    nidn_nim = models.CharField(max_length=20, blank=True, verbose_name='NIDN/NIM')
    urutan = models.IntegerField(default=1)
    afiliasi = models.CharField(max_length=200, blank=True)
    peran = models.CharField(max_length=25, choices=PERAN_PENULIS_CHOICES, default='anggota_penulis')
    corresponding_author = models.BooleanField(default=False)

    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Penulis Paten/HKI'
        verbose_name_plural = 'Penulis Paten/HKI'
        ordering = ['urutan']

    def __str__(self):
        return f"{self.paten_hki.judul_karya[:40]} - {self.nama}"
