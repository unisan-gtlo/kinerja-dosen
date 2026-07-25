"""Kategori SISTER 'Pelaks. Pengabdian' -- Pengabdian, Pembicara, Pengelola
Jurnal, Jabatan Struktural. Field mengikuti Pelaksanaan Pegabdian.docx
(screenshot form SISTER asli).

Pengabdian menggantikan kinerja.PKM (model lama, verbose_name-nya sudah
"Pengabdian Masyarakat") -- related_name FK sengaja dipertahankan
'pkm_set' supaya semua pemanggil .pkm_set di dashboard/laporan tidak perlu
diubah, sama pola dengan penelitian_set/publikasi_set/hki_set di app
penelitian.

Beberapa dropdown di form asli (Afiliasi, Kelompok Bidang, Jenis SKIM,
Kategori Capaian Luaran, Kategori Pembicara, Tingkat Pertemuan, Media
Publikasi, Jabatan Tugas) sengaja dibuat CharField bebas karena daftar
pilihan lengkapnya tidak terlihat jelas di screenshot referensi.

Anggota Pengabdian dipilih dari referensi SIMDA (id polos + snapshot nama),
sama pola dengan AnggotaPenelitian -- lihat catatan di app pendidikan untuk
alasan tidak pakai FK lintas-database.
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


class Pengabdian(models.Model):
    KATEGORI_KEGIATAN = [
        ('pengembangan_hasil', 'Melaksanakan pengembangan hasil pendidikan dan penelitian'),
        ('pelayanan_masyarakat', 'Memberi pelayanan kepada masyarakat atau kegiatan lain yang menunjang pelaksanaan tugas umum pemerintah dan pembangunan'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pkm_set')
    kode_prodi = models.CharField(max_length=10, blank=True, null=True)
    kode_fakultas = models.CharField(max_length=10, blank=True, null=True)

    kategori_kegiatan = models.CharField(max_length=25, choices=KATEGORI_KEGIATAN)
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
        verbose_name = 'Pengabdian'
        verbose_name_plural = 'Pengabdian'
        ordering = ['-tahun_pelaksanaan']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.judul_kegiatan[:50]}"

    @property
    def total_dana(self):
        return (self.dana_dikti or 0) + (self.dana_pt or 0) + (self.dana_institusi_lain or 0)

    @property
    def periode(self):
        return f"{self.semester} {self.tahun_akademik}" if self.semester else self.tahun_kegiatan


class AnggotaPengabdian(models.Model):
    """Anggota Kegiatan (Dosen/Mahasiswa/Kolaborator Eksternal) di Pengabdian.
    Sama pola dengan AnggotaPenelitian -- cuma Peran (Ketua/Anggota) +
    Status Aktif, tanpa urutan/afiliasi/corresponding author."""
    JENIS_ANGGOTA = [
        ('dosen', 'Dosen'),
        ('mahasiswa', 'Mahasiswa'),
        ('kolaborator_eksternal', 'Kolaborator Eksternal'),
    ]

    pengabdian = models.ForeignKey(Pengabdian, on_delete=models.CASCADE, related_name='anggota_set')
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
        verbose_name = 'Anggota Pengabdian'
        verbose_name_plural = 'Anggota Pengabdian'
        ordering = ['jenis_anggota', 'id']

    def __str__(self):
        return f"{self.pengabdian.judul_kegiatan[:40]} - {self.nama}"


class Pembicara(models.Model):
    KATEGORI_KEGIATAN = [
        ('terjadwal_semester_internasional', 'Terjadwal/terprogram dalam satu semester atau lebih (tingkat internasional)'),
        ('terjadwal_semester_nasional', 'Terjadwal/terprogram dalam satu semester atau lebih (tingkat nasional)'),
        ('terjadwal_semester_lokal', 'Terjadwal/terprogram dalam satu semester atau lebih (tingkat lokal)'),
        ('terjadwal_bulan_internasional', 'Terjadwal/terprogram kurang dari satu semester dan minimal satu bulan (tingkat internasional)'),
        ('terjadwal_bulan_nasional', 'Terjadwal/terprogram kurang dari satu semester dan minimal satu bulan (tingkat nasional)'),
        ('terjadwal_bulan_lokal', 'Terjadwal/terprogram kurang dari satu semester dan minimal satu bulan (tingkat lokal)'),
        ('insidential_internasional', 'Insidential (tingkat internasional)'),
        ('insidential_nasional', 'Insidential (tingkat nasional)'),
        ('insidential_lokal', 'Insidential (tingkat lokal)'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pembicara_set')
    kode_prodi = models.CharField(max_length=10, blank=True, null=True)
    kode_fakultas = models.CharField(max_length=10, blank=True, null=True)

    kategori_kegiatan = models.CharField(max_length=40, choices=KATEGORI_KEGIATAN)
    kategori_capaian_luaran = models.CharField(max_length=150, blank=True)
    litabmas = models.CharField(max_length=200, blank=True)
    kategori_pembicara = models.CharField(max_length=100, blank=True)
    judul_makalah = models.TextField()
    nama_pertemuan_ilmiah = models.CharField(max_length=200)
    tingkat_pertemuan = models.CharField(max_length=100, blank=True)
    penyelenggara = models.CharField(max_length=200)
    tanggal_pelaksanaan = models.DateField()
    bahasa = models.CharField(max_length=50, blank=True)
    no_sk_penugasan = models.CharField(max_length=100, blank=True)
    tanggal_sk_penugasan = models.DateField(null=True, blank=True)

    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES, blank=True, null=True)
    tahun_akademik = models.CharField(max_length=10, blank=True, null=True)
    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Pembicara'
        verbose_name_plural = 'Pembicara'
        ordering = ['-tanggal_pelaksanaan']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.judul_makalah[:50]}"

    @property
    def periode(self):
        return f"{self.semester} {self.tahun_akademik}" if self.semester else str(self.tanggal_pelaksanaan.year)


class PengelolaJurnal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='jurnal_set')
    kode_prodi = models.CharField(max_length=10, blank=True, null=True)
    kode_fakultas = models.CharField(max_length=10, blank=True, null=True)

    nama_jurnal = models.CharField(max_length=200)
    media_publikasi = models.CharField(max_length=150, blank=True)
    peran = models.CharField(max_length=100)
    no_sk_penugasan = models.CharField(max_length=100, blank=True)
    terhitung_mulai_tanggal = models.DateField()
    tanggal_selesai = models.DateField(null=True, blank=True)
    status_aktif = models.BooleanField(default=True)

    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES, blank=True, null=True)
    tahun_akademik = models.CharField(max_length=10, blank=True, null=True)
    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Pengelola Jurnal'
        verbose_name_plural = 'Pengelola Jurnal'
        ordering = ['-terhitung_mulai_tanggal']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.nama_jurnal[:50]}"

    @property
    def periode(self):
        return f"{self.semester} {self.tahun_akademik}" if self.semester else str(self.terhitung_mulai_tanggal.year)


class JabatanStruktural(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='jabatan_set')
    kode_prodi = models.CharField(max_length=10, blank=True, null=True)
    kode_fakultas = models.CharField(max_length=10, blank=True, null=True)

    jabatan_tugas = models.CharField(max_length=150)
    no_sk_jabatan_struktural = models.CharField(max_length=100, blank=True, verbose_name='Nomor SK Jabatan Struktural')
    terhitung_mulai_tanggal = models.DateField()
    terhitung_selesai_tanggal = models.DateField(null=True, blank=True)
    lokasi_penugasan = models.CharField(max_length=200)

    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES, blank=True, null=True)
    tahun_akademik = models.CharField(max_length=10, blank=True, null=True)
    tgl_input = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Jabatan Struktural'
        verbose_name_plural = 'Jabatan Struktural'
        ordering = ['-terhitung_mulai_tanggal']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.jabatan_tugas}"

    @property
    def periode(self):
        return f"{self.semester} {self.tahun_akademik}" if self.semester else str(self.terhitung_mulai_tanggal.year)
