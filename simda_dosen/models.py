"""Model unmanaged (managed=False) yang mem-mirror skema asli SIMDA
(database 'unisan_db', schema Postgres 'master'). Tidak pernah dimigrasi
dari SIKD -- skema tabel dikelola sepenuhnya oleh SIMDA (repo C:\\unisan\\simda).

Field dibagi dua kelompok lewat komentar:
- SELF-SERVICE: boleh diedit dosen sendiri lewat SIKD.
- ADMIN/HR (read-only di SIKD): field struktural/kepegawaian, tetap
  diedit lewat Django admin SIMDA seperti sekarang. Views SIKD tidak
  boleh expose field ini di form edit dosen.

Lihat C:\\unisan\\simda\\sdm\\models.py untuk skema aslinya, dan
C:\\unisan\\simda\\buat_role_sikd_rw.sql untuk grant akses baca-tulisnya.
"""
from django.core.exceptions import ValidationError
from django.db import models

from .storage import simda_media_storage


def validate_file_size(value):
    """Sama seperti sdm.models.validate_file_size di SIMDA -- maks 500KB,
    supaya konsisten dengan validator di sisi SIMDA. Ini berfungsi
    sebagai safety-net SETELAH compress_uploaded_file() (lihat
    simda_dosen/file_compress.py) -- harusnya jarang kena, kecuali
    kompresi gagal mencapai target di kasus ekstrem."""
    limit_kb = 500
    try:
        ukuran = value.size
    except (FileNotFoundError, OSError):
        # File rujukan sudah tidak ada fisiknya di storage -- jangan sampai
        # full_clean() gagal total dan memblokir simpan field lain yang valid.
        return
    if ukuran > limit_kb * 1024:
        raise ValidationError(
            f'Ukuran file maksimal {limit_kb} KB. '
            f'File Anda: {ukuran / 1024:.0f} KB.'
        )


class DataDosen(models.Model):
    JENIS_KEL = [('L', 'Laki-laki'), ('P', 'Perempuan')]
    STATUS_NIKAH = [('Belum Menikah', 'Belum Menikah'), ('Menikah', 'Menikah'),
                     ('Duda', 'Duda'), ('Janda', 'Janda')]
    PENDIDIKAN = [('D3', 'D3'), ('D4', 'D4'), ('S1', 'S1'), ('S2', 'S2'), ('S3', 'S3'),
                  ('Sp1', 'Sp-1'), ('Sp2', 'Sp-2'), ('Prof', 'Profesi')]

    # ── ADMIN/HR (read-only di SIKD) ──────────────────────────────
    nidn = models.CharField(max_length=20, unique=True, db_index=True)
    nip = models.CharField(max_length=30, blank=True)
    nip_yayasan = models.CharField(max_length=30, blank=True)
    kode_fakultas = models.CharField(max_length=10, db_column='kode_fakultas')
    kode_prodi = models.CharField(max_length=10, db_column='kode_prodi')
    jenis_kepegawaian_id = models.IntegerField(null=True, blank=True)
    status_kepegawaian_id = models.IntegerField(null=True, blank=True)
    jabatan_fungsional_id = models.IntegerField(null=True, blank=True)
    golongan_id = models.IntegerField(null=True, blank=True)
    pendidikan_terakhir = models.CharField(max_length=5, choices=PENDIDIKAN, blank=True)
    tgl_mulai_kerja = models.DateField(null=True, blank=True)
    id_serdos = models.CharField(max_length=30, blank=True)
    nama_bank = models.CharField(max_length=50, blank=True)
    no_rekening = models.CharField(max_length=30, blank=True)
    atas_nama_rekening = models.CharField(max_length=100, blank=True)

    # bidang_keahlian_id/no_sk_pengangkatan/tgl_sk_pengangkatan/
    # file_sk_pengangkatan awalnya masuk kategori admin/HR di atas, tapi
    # sifatnya (berbasis SK, snapshot sekali per dosen) sama dengan
    # Jabatan Fungsional/Pangkat yang sudah self-service -- dibuka jadi
    # editable dosen lewat tab Profil Dasar (lihat profil/views.py::simpan_profil).
    bidang_keahlian_id = models.IntegerField(null=True, blank=True)
    no_sk_pengangkatan = models.CharField(max_length=100, blank=True)
    tgl_sk_pengangkatan = models.DateField(null=True, blank=True)
    file_sk_pengangkatan = models.FileField(upload_to='dosen/sk_pengangkatan/', null=True, blank=True,
                                             validators=[validate_file_size], storage=simda_media_storage)
    is_active = models.BooleanField(default=True)
    tgl_dibuat = models.DateTimeField(auto_now_add=True)
    tgl_diperbarui = models.DateTimeField(auto_now=True)

    # ── SELF-SERVICE (boleh diedit dosen lewat SIKD) ──────────────
    nuptk = models.CharField(max_length=20, blank=True, db_index=True,
                              verbose_name='NUPTK')
    nama_lengkap = models.CharField(max_length=150)
    gelar_depan = models.CharField(max_length=50, blank=True)
    gelar_belakang = models.CharField(max_length=100, blank=True)
    jenis_kelamin = models.CharField(max_length=1, choices=JENIS_KEL)
    tempat_lahir = models.CharField(max_length=100, blank=True)
    tgl_lahir = models.DateField(null=True, blank=True)
    agama_id = models.IntegerField(null=True, blank=True,
                                    help_text='FK id ke referensi.Agama SIMDA (belum di-mirror, lookup terpisah kalau perlu label)')
    status_pernikahan = models.CharField(max_length=20, choices=STATUS_NIKAH, blank=True)
    alamat_domisili = models.TextField(blank=True)
    kabupaten_domisili_id = models.IntegerField(null=True, blank=True)
    provinsi_domisili_id = models.IntegerField(null=True, blank=True)
    kode_pos = models.CharField(max_length=10, blank=True)
    no_hp = models.CharField(max_length=20, blank=True)
    email_pribadi = models.EmailField(blank=True)
    email_kampus = models.EmailField(blank=True)
    id_sinta = models.CharField(max_length=20, blank=True, verbose_name='ID SINTA')
    id_scopus = models.CharField(max_length=50, blank=True, verbose_name='Scopus Author ID')
    id_google_scholar = models.CharField(max_length=100, blank=True, verbose_name='Google Scholar ID')
    orcid = models.CharField(max_length=19, blank=True, verbose_name='ORCID')
    id_garuda = models.CharField(max_length=20, blank=True, verbose_name='ID Garuda')
    h_index_sinta = models.IntegerField(null=True, blank=True)
    h_index_scopus = models.IntegerField(null=True, blank=True)
    nira = models.CharField(max_length=30, blank=True)
    minat_penelitian = models.TextField(blank=True)
    foto = models.ImageField(upload_to='dosen/foto/', null=True, blank=True,
                              validators=[validate_file_size], storage=simda_media_storage)
    file_ktp = models.FileField(upload_to='dosen/ktp/', null=True, blank=True,
                                 validators=[validate_file_size], storage=simda_media_storage)
    file_npwp = models.FileField(upload_to='dosen/npwp/', null=True, blank=True,
                                  validators=[validate_file_size], storage=simda_media_storage)
    npwp = models.CharField(max_length=20, blank=True)
    nik = models.CharField(max_length=20, blank=True)

    # Field yang boleh diedit dosen sendiri lewat form profil SIKD.
    SELF_SERVICE_FIELDS = [
        'nuptk', 'nama_lengkap', 'gelar_depan', 'gelar_belakang',
        'jenis_kelamin', 'tempat_lahir', 'tgl_lahir', 'agama_id',
        'status_pernikahan', 'alamat_domisili', 'kabupaten_domisili_id',
        'provinsi_domisili_id', 'kode_pos', 'no_hp', 'email_pribadi',
        'id_sinta', 'id_scopus', 'id_google_scholar', 'orcid', 'id_garuda',
        'h_index_sinta', 'h_index_scopus', 'nira', 'minat_penelitian',
        'foto', 'file_ktp', 'file_npwp', 'npwp', 'nik',
    ]

    class Meta:
        managed = False
        db_table = 'master"."data_dosen'
        verbose_name = 'Data Dosen (SIMDA)'
        verbose_name_plural = 'Data Dosen (SIMDA)'

    def __str__(self):
        gelar = f'{self.gelar_depan} ' if self.gelar_depan else ''
        belakang = f', {self.gelar_belakang}' if self.gelar_belakang else ''
        return f'{gelar}{self.nama_lengkap}{belakang}'

    @property
    def nama_lengkap_gelar(self):
        gelar = f'{self.gelar_depan} ' if self.gelar_depan else ''
        belakang = f', {self.gelar_belakang}' if self.gelar_belakang else ''
        return f'{gelar}{self.nama_lengkap}{belakang}'

    @property
    def jabatan_fungsional_nama(self):
        """Nama jabfung aktif (cache admin) -- lookup ke view referensi. N+1
        kalau dipanggil dalam loop besar, tapi skala dosen SIKD kecil (~150)."""
        if not self.jabatan_fungsional_id:
            return ''
        jf = JabatanFungsionalPublik.objects.using('simda').filter(
            id=self.jabatan_fungsional_id).first()
        return jf.nama if jf else ''

    @property
    def golongan_nama(self):
        """Golongan/Pangkat aktif (cache, disinkron dari Riwayat Pangkat/
        Golongan yang TMT-nya paling akhir -- lihat
        simda_dosen.utils.sync_golongan_terakhir)."""
        if not self.golongan_id:
            return ''
        g = GolonganPublik.objects.using('simda').filter(id=self.golongan_id).first()
        return f'{g.kode} ({g.pangkat})' if g else ''

    @property
    def bidang_keahlian_nama(self):
        if not self.bidang_keahlian_id:
            return ''
        bk = BidangKeahlianPublik.objects.using('simda').filter(
            id=self.bidang_keahlian_id).first()
        return bk.nama if bk else ''

    @property
    def jenis_kepegawaian_nama(self):
        if not self.jenis_kepegawaian_id:
            return ''
        jk = JenisKepegawaianPublik.objects.using('simda').filter(
            id=self.jenis_kepegawaian_id).first()
        return jk.nama if jk else ''

    @property
    def status_kepegawaian_nama(self):
        if not self.status_kepegawaian_id:
            return ''
        sk = StatusKepegawaianPublik.objects.using('simda').filter(
            id=self.status_kepegawaian_id).first()
        return sk.nama if sk else ''

    @property
    def persentase_kelengkapan(self):
        """Kelengkapan profil berdasarkan field yang ada di SIMDA (beda
        definisi dari versi lama SIKD yang mengecek jabfung_aktif/
        bidang_keahlian/mata_kuliah_diampu -- field itu tidak ada di SIMDA)."""
        fields = [
            self.nik, self.tempat_lahir, self.tgl_lahir,
            self.jenis_kelamin, self.agama_id, self.alamat_domisili,
            self.email_pribadi, self.pendidikan_terakhir,
            self.foto, self.file_ktp,
        ]
        filled = sum(1 for f in fields if f)
        return int((filled / len(fields)) * 100)


class RiwayatJabatanFungsional(models.Model):
    dosen = models.ForeignKey(DataDosen, on_delete=models.DO_NOTHING,
                               related_name='riwayat_jabfung', db_column='dosen_id')
    jabatan_fungsional_id = models.IntegerField()
    no_sk = models.CharField(max_length=100, blank=True)
    tgl_sk = models.DateField(null=True, blank=True)
    tmt = models.DateField(null=True, blank=True, verbose_name='TMT')
    tgl_selesai = models.DateField(null=True, blank=True)
    angka_kredit = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    file_sk = models.FileField(upload_to='dosen/jabfung_sk/', null=True, blank=True,
                                validators=[validate_file_size], storage=simda_media_storage)
    url_sk = models.URLField(blank=True, verbose_name='Link SK (alternatif)')
    keterangan = models.TextField(blank=True)

    class Meta:
        managed = False
        db_table = 'master"."riwayat_jabfung'
        verbose_name = 'Riwayat Jabatan Fungsional (SIMDA)'
        verbose_name_plural = 'Riwayat Jabatan Fungsional (SIMDA)'
        ordering = ['-tmt']

    def __str__(self):
        return f'{self.dosen.nidn} — jabfung {self.tmt}'

    @property
    def jabatan_fungsional_nama(self):
        if not self.jabatan_fungsional_id:
            return ''
        jf = JabatanFungsionalPublik.objects.using('simda').filter(
            id=self.jabatan_fungsional_id).first()
        return jf.nama if jf else ''


class RiwayatPangkatGolongan(models.Model):
    """Riwayat kepangkatan/inpassing PNS (skala I/a-IV/e) -- beda dimensi
    dari Jabatan Fungsional. Sesuai form SISTER "Form Tambah Inpassing"."""
    dosen = models.ForeignKey(DataDosen, on_delete=models.DO_NOTHING,
                               related_name='riwayat_pangkat_golongan', db_column='dosen_id')
    golongan_id = models.IntegerField()
    no_sk = models.CharField(max_length=100, verbose_name='Nomor SK Inpassing')
    tgl_sk = models.DateField(null=True, blank=True, verbose_name='Tanggal SK')
    tmt = models.DateField(verbose_name='TMT')
    angka_kredit = models.DecimalField(max_digits=8, decimal_places=2)
    masa_kerja_tahun = models.IntegerField(default=0, verbose_name='Masa Kerja (Tahun)')
    masa_kerja_bulan = models.IntegerField(default=0, verbose_name='Masa Kerja (Bulan)')
    file_sk = models.FileField(upload_to='dosen/pangkat_sk/', null=True, blank=True,
                                validators=[validate_file_size], storage=simda_media_storage)
    url_sk = models.URLField(blank=True, verbose_name='Link SK (alternatif)')

    class Meta:
        managed = False
        db_table = 'master"."riwayat_pangkat_golongan'
        verbose_name = 'Riwayat Pangkat/Golongan (SIMDA)'
        verbose_name_plural = 'Riwayat Pangkat/Golongan (SIMDA)'
        ordering = ['-tmt']

    def __str__(self):
        return f'{self.dosen.nidn} — pangkat {self.tmt}'

    @property
    def golongan_display(self):
        if not self.golongan_id:
            return ''
        g = GolonganPublik.objects.using('simda').filter(id=self.golongan_id).first()
        return f'{g.kode} ({g.pangkat})' if g else ''


class RiwayatPendidikanDosen(models.Model):
    JENJANG = [('S1', 'S1'), ('S2', 'S2'), ('S3', 'S3')]

    dosen = models.ForeignKey(DataDosen, on_delete=models.DO_NOTHING,
                               related_name='riwayat_pendidikan', db_column='dosen_id')
    jenjang = models.CharField(max_length=5, choices=JENJANG)
    institusi = models.CharField(max_length=200)
    pt_asal_id = models.IntegerField(null=True, blank=True)
    prodi_studi = models.CharField(max_length=150, blank=True)
    tahun_masuk = models.IntegerField(null=True, blank=True)
    tahun_lulus = models.IntegerField(null=True, blank=True)
    no_ijazah = models.CharField(max_length=50, blank=True)
    judul_thesis = models.TextField(blank=True, verbose_name='Judul Skripsi/Tesis/Disertasi')
    file_ijazah = models.FileField(upload_to='dosen/ijazah/', null=True, blank=True,
                                    validators=[validate_file_size], storage=simda_media_storage)
    url_ijazah = models.URLField(blank=True)
    file_transkrip = models.FileField(upload_to='dosen/transkrip/', null=True, blank=True,
                                       validators=[validate_file_size], storage=simda_media_storage)
    url_transkrip = models.URLField(blank=True)

    class Meta:
        managed = False
        db_table = 'master"."riwayat_pendidikan_dosen'
        verbose_name = 'Riwayat Pendidikan Dosen (SIMDA)'
        verbose_name_plural = 'Riwayat Pendidikan Dosen (SIMDA)'
        ordering = ['-jenjang']

    def __str__(self):
        return f'{self.dosen.nidn} — {self.jenjang} {self.institusi}'


class RiwayatBKD(models.Model):
    STATUS_PENGESAHAN = [
        ('belum', 'Belum Disahkan'),
        ('disahkan', 'Disahkan'),
        ('ditolak', 'Ditolak'),
    ]

    dosen = models.ForeignKey(DataDosen, on_delete=models.DO_NOTHING,
                               related_name='riwayat_bkd', db_column='dosen_id')
    periode = models.ForeignKey('TahunAkademikPublik', on_delete=models.DO_NOTHING,
                                 related_name='riwayat_bkd', db_column='periode_id')
    sks_pengajaran = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    sks_penelitian = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    sks_pkm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    sks_penunjang = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    file_bkd = models.FileField(upload_to='dosen/bkd/', null=True, blank=True,
                                 validators=[validate_file_size], verbose_name='File BKD',
                                 storage=simda_media_storage)
    link_bkd = models.URLField(blank=True, verbose_name='Link BKD (alternatif)')
    status_pengesahan = models.CharField(max_length=20, choices=STATUS_PENGESAHAN, default='belum')
    keterangan = models.TextField(blank=True)
    tgl_upload = models.DateTimeField(auto_now_add=True)
    tgl_diperbarui = models.DateTimeField(auto_now=True)

    # Hanya role ini yang boleh mengubah status_pengesahan lewat SIKD --
    # dosen pemilik record tidak boleh mengesahkan BKD-nya sendiri.
    ROLE_BOLEH_SAHKAN = ['admin', 'kaprodi', 'sekprodi', 'dekan', 'wadek', 'rektorat']

    class Meta:
        managed = False
        db_table = 'master"."riwayat_bkd'
        verbose_name = 'Riwayat BKD (SIMDA)'
        verbose_name_plural = 'Riwayat BKD (SIMDA)'
        ordering = ['-periode_id']

    def __str__(self):
        return f'{self.dosen.nidn} — BKD periode {self.periode_id}'

    @property
    def total_sks(self):
        return sum([
            self.sks_pengajaran or 0,
            self.sks_penelitian or 0,
            self.sks_pkm or 0,
            self.sks_penunjang or 0,
        ])


class AgamaPublik(models.Model):
    """Read-only, sumbernya master.v_agama_publik (view SIMDA). Dipakai
    untuk dropdown agama -- id-nya dipakai sebagai DataDosen.agama_id."""
    id = models.IntegerField(primary_key=True)
    kode = models.CharField(max_length=10)
    nama = models.CharField(max_length=50)
    urutan = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'master"."v_agama_publik'
        verbose_name = 'Agama (SIMDA)'
        verbose_name_plural = 'Agama (SIMDA)'
        ordering = ['urutan']

    def __str__(self):
        return self.nama


class JabatanFungsionalPublik(models.Model):
    """Read-only, sumbernya master.v_jabatan_fungsional_publik (view SIMDA).
    Dipakai untuk dropdown jabfung -- id-nya dipakai sebagai
    RiwayatJabatanFungsional.jabatan_fungsional_id."""
    id = models.IntegerField(primary_key=True)
    kode = models.CharField(max_length=10)
    nama = models.CharField(max_length=100)
    singkatan = models.CharField(max_length=10, blank=True)
    urutan = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'master"."v_jabatan_fungsional_publik'
        verbose_name = 'Jabatan Fungsional (SIMDA)'
        verbose_name_plural = 'Jabatan Fungsional (SIMDA)'
        ordering = ['urutan']

    def __str__(self):
        return self.nama


class GolonganPublik(models.Model):
    """Read-only, sumbernya master.v_golongan_publik (view SIMDA). Dipakai
    untuk dropdown Golongan/Pangkat (skala I/a-IV/e) -- id-nya dipakai
    sebagai RiwayatPangkatGolongan.golongan_id."""
    id = models.IntegerField(primary_key=True)
    kode = models.CharField(max_length=5)
    nama = models.CharField(max_length=50)
    pangkat = models.CharField(max_length=100, blank=True)
    urutan = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'master"."v_golongan_publik'
        verbose_name = 'Golongan (SIMDA)'
        verbose_name_plural = 'Golongan (SIMDA)'
        ordering = ['urutan']

    def __str__(self):
        return f'{self.kode} ({self.pangkat})'


class BidangKeahlian(models.Model):
    """Writable, tabel mentah master.bidang_keahlian (bukan view) -- dipakai
    untuk auto-create entri baru saat dosen mengetik Bidang Keahlian yang
    belum ada di daftar (self-service, lihat
    simda_dosen.utils.get_or_create_bidang_keahlian & profil/views.py
    simpan_profil). sikd_rw cuma dikasih SELECT+INSERT ke tabel ini (bukan
    UPDATE/DELETE) supaya tidak bisa mengubah/menghapus entri kurasi admin
    yang sudah ada -- lihat buat_grant_bidang_keahlian_selfservice.sql."""
    kode = models.CharField(max_length=20, unique=True)
    nama = models.CharField(max_length=150)
    rumpun_ilmu = models.CharField(max_length=50, blank=True)
    status = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'master"."bidang_keahlian'
        verbose_name = 'Bidang Keahlian (tulis)'
        verbose_name_plural = 'Bidang Keahlian (tulis)'
        ordering = ['nama']

    def __str__(self):
        return self.nama


class BidangKeahlianPublik(models.Model):
    """Read-only, sumbernya master.v_bidang_keahlian_publik (view SIMDA).
    Dipakai untuk dropdown Bidang Keahlian/Keilmuan di tab Profil Dasar --
    id-nya dipakai sebagai DataDosen.bidang_keahlian_id."""
    id = models.IntegerField(primary_key=True)
    kode = models.CharField(max_length=20)
    nama = models.CharField(max_length=150)
    rumpun_ilmu = models.CharField(max_length=50, blank=True)

    class Meta:
        managed = False
        db_table = 'master"."v_bidang_keahlian_publik'
        verbose_name = 'Bidang Keahlian (SIMDA)'
        verbose_name_plural = 'Bidang Keahlian (SIMDA)'
        ordering = ['nama']

    def __str__(self):
        return self.nama


class JenisKepegawaianPublik(models.Model):
    """Read-only, sumbernya master.v_jenis_kepegawaian_publik (view SIMDA).
    Dipakai untuk dropdown Status Kepegawaian (tipe: Tetap Yayasan/
    Kontrak/Paruh Waktu/Tidak Tetap) -- id-nya dipakai sebagai
    DataDosen.jenis_kepegawaian_id."""
    id = models.IntegerField(primary_key=True)
    kode = models.CharField(max_length=20)
    nama = models.CharField(max_length=100)
    urutan = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'master"."v_jenis_kepegawaian_publik'
        verbose_name = 'Jenis Kepegawaian (SIMDA)'
        verbose_name_plural = 'Jenis Kepegawaian (SIMDA)'
        ordering = ['urutan']

    def __str__(self):
        return self.nama


class StatusKepegawaianPublik(models.Model):
    """Read-only, sumbernya master.v_status_kepegawaian_publik (view
    SIMDA). Dipakai untuk dropdown Status Keaktifan (Aktif/Izin Belajar/
    Tugas Belajar/Mutasi/Wafat) -- id-nya dipakai sebagai
    DataDosen.status_kepegawaian_id. Sejak sesi ini menggantikan field
    lama accounts.User.status_kepegawaian (lihat migrasi data terkait)."""
    id = models.IntegerField(primary_key=True)
    kode = models.CharField(max_length=20)
    nama = models.CharField(max_length=50)
    urutan = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'master"."v_status_kepegawaian_publik'
        verbose_name = 'Status Keaktifan (SIMDA)'
        verbose_name_plural = 'Status Keaktifan (SIMDA)'
        ordering = ['urutan']

    def __str__(self):
        return self.nama


class FakultasPublik(models.Model):
    """Read-only, sumbernya master.v_fakultas_publik (view SIMDA). Dipakai
    untuk dropdown -- SIKD tidak pernah menulis ke tabel Fakultas."""
    kode_fakultas = models.CharField(max_length=10, primary_key=True)
    nama_fakultas = models.CharField(max_length=150)
    nama_singkat = models.CharField(max_length=30, blank=True)
    status = models.CharField(max_length=10)

    class Meta:
        managed = False
        db_table = 'master"."v_fakultas_publik'
        verbose_name = 'Fakultas (SIMDA)'
        verbose_name_plural = 'Fakultas (SIMDA)'

    def __str__(self):
        return self.nama_fakultas


class ProdiPublik(models.Model):
    """Read-only, sumbernya master.v_prodi_publik (view SIMDA)."""
    kode_prodi = models.CharField(max_length=10, primary_key=True)
    kode_fakultas = models.CharField(max_length=10)
    nama_prodi = models.CharField(max_length=150)
    jenjang = models.CharField(max_length=10)
    status = models.CharField(max_length=10)

    class Meta:
        managed = False
        db_table = 'master"."v_prodi_publik'
        verbose_name = 'Program Studi (SIMDA)'
        verbose_name_plural = 'Program Studi (SIMDA)'

    def __str__(self):
        return self.nama_prodi


class TahunAkademikPublik(models.Model):
    """Read-only, sumbernya master.v_tahun_akademik_publik (view SIMDA)."""
    id = models.IntegerField(primary_key=True)
    tahun_akademik = models.CharField(max_length=10)
    semester_aktif = models.CharField(max_length=10)
    label_lengkap = models.CharField(max_length=50, blank=True)
    urutan = models.IntegerField()
    is_aktif = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'master"."v_tahun_akademik_publik'
        verbose_name = 'Tahun Akademik (SIMDA)'
        verbose_name_plural = 'Tahun Akademik (SIMDA)'
        ordering = ['-urutan']

    def __str__(self):
        return self.label_lengkap or self.tahun_akademik


class MataKuliahPublik(models.Model):
    """Read-only, sumbernya master.mata_kuliah langsung (tabel mentah,
    bukan view -- katalog MK tidak berisi data pribadi/sensitif). Dipakai
    untuk dropdown+cari Mata Kuliah di form Pengajaran (app pendidikan),
    difilter per kode_prodi dosen yang login."""
    JENIS = [('Wajib', 'Wajib'), ('Pilihan', 'Pilihan'), ('KKN', 'KKN'),
             ('Skripsi', 'Skripsi'), ('Tesis', 'Tesis'), ('Magang', 'Magang')]

    kode_mk = models.CharField(max_length=20)
    kode_mk_dikti = models.CharField(max_length=20, blank=True)
    nama_mk = models.CharField(max_length=200)
    kode_prodi = models.CharField(max_length=10, db_column='kode_prodi')
    sks_total = models.IntegerField()
    jenis_mk = models.CharField(max_length=20, choices=JENIS)
    status = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'master"."mata_kuliah'
        verbose_name = 'Mata Kuliah (SIMDA)'
        verbose_name_plural = 'Mata Kuliah (SIMDA)'
        ordering = ['kode_prodi', 'kode_mk']

    def __str__(self):
        return f'{self.kode_mk} — {self.nama_mk} ({self.sks_total} SKS)'


class MahasiswaPublik(models.Model):
    """Read-only, sumbernya master.v_mahasiswa_publik (view SIMDA -- field
    sensitif seperti NIK/alamat/data orang tua SENGAJA tidak disertakan,
    lihat buat_view_mahasiswa_publik.sql di repo SIMDA). Dipakai untuk
    dropdown+cari Nama Mahasiswa di form Bimbingan & Pengujian Mahasiswa
    (app pendidikan), difilter per kode_prodi."""
    nim = models.CharField(max_length=20)
    nama_lengkap = models.CharField(max_length=150)
    kode_prodi = models.CharField(max_length=10, db_column='kode_prodi')
    angkatan = models.CharField(max_length=10)
    semester_aktif = models.IntegerField()
    status_mahasiswa = models.CharField(max_length=25)

    class Meta:
        managed = False
        db_table = 'master"."v_mahasiswa_publik'
        verbose_name = 'Mahasiswa (SIMDA)'
        verbose_name_plural = 'Mahasiswa (SIMDA)'
        ordering = ['kode_prodi', 'nama_lengkap']

    def __str__(self):
        return f'{self.nim} — {self.nama_lengkap}'


class UnitKerja(models.Model):
    """Sumbernya master.unit_kerja (tabel katalog organisasi -- BUKAN data
    pribadi/sensitif, sama seperti master.mata_kuliah, jadi aman diakses
    langsung tanpa lewat view tersaring). Dipakai sebagai dropdown unit
    kerja di form Kelola Data Tendik. Awalnya read-only, sekarang JUGA
    bisa ditulis (lihat get_or_create_unit_kerja di utils.py) untuk fitur
    "ketik langsung Unit Kerja yang belum ada di dropdown, otomatis
    tersimpan sebagai opsi baru" -- pola sama dengan Bidang Keahlian/
    Keilmuan di Profil Dosen. `induk_id` disimpan sebagai id mentah
    (bukan FK self-referencing) -- form Kelola Data Tendik cuma butuh
    daftar datar (flat), tidak perlu render struktur pohon unit/sub-unit."""
    JENIS = [
        ('akademik', 'Akademik'), ('administrasi', 'Administrasi'),
        ('penunjang', 'Penunjang'), ('layanan', 'Layanan'), ('penelitian', 'Penelitian'),
    ]

    kode = models.CharField(max_length=20, unique=True)
    nama = models.CharField(max_length=150)
    singkatan = models.CharField(max_length=30, blank=True)
    jenis = models.CharField(max_length=20, choices=JENIS)
    induk_id = models.IntegerField(null=True, blank=True)
    email = models.EmailField(blank=True)
    no_telepon = models.CharField(max_length=20, blank=True)
    status = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'master"."unit_kerja'
        verbose_name = 'Unit Kerja (SIMDA)'
        verbose_name_plural = 'Unit Kerja (SIMDA)'
        ordering = ['jenis', 'nama']

    def __str__(self):
        return f'{self.singkatan or self.kode} — {self.nama}'


class DataTendik(models.Model):
    """CRUD PENUH lewat tabel mentah master.data_tendik (BUKAN lagi view
    tersaring v_tendik_ringkas) -- lihat C:\\unisan\\simda\\sdm\\models.py
    untuk skema aslinya dan C:\\unisan\\simda\\tambah_akses_tendik_penuh.sql
    untuk grant SELECT/INSERT/UPDATE/DELETE-nya.

    **Keputusan per fitur "Kelola Data Tendik" (2026-08-01):** awalnya
    model ini SENGAJA dibuat read-only lewat view (lihat riwayat git) --
    SIKD dulu tidak punya fitur apa pun yang butuh MENULIS data tendik.
    Sekarang SIKD jadi entry-point CRUD penuh untuk data tendik (user
    eksplisit minta cakupan field selengkap tabel SIMDA aslinya, termasuk
    NIK/rekening/NPWP/foto), jadi sikd_rw dinaikkan ke akses baca-tulis
    penuh ke tabel mentah, sama pola dengan master.data_dosen di
    buat_role_sikd_rw.sql. Pembuatan akun LOGIN (accounts.User) TETAP
    langkah terpisah lewat Kelola User (nip_yayasan diisi manual) --
    TIDAK auto-dibuatkan dari sini, konsisten dengan pola Dosen.

    Dicocokkan ke accounts.User lewat nip_yayasan (tendik tidak punya
    NIDN). provinsi_domisili_id/kabupaten_domisili_id SENGAJA tidak
    diberi dropdown di form (disimpan sebagai id mentah saja) -- sama
    seperti gap yang sudah ada di form Profil Dosen (`profil/views.py`
    tidak pernah mengekspos kedua field itu juga), karena app `wilayah`
    SIMDA (Provinsi/KabupatenKota) belum di-mirror ke SIKD sama sekali;
    membangun mirror+dropdown baru untuk itu di luar cakupan fitur ini."""
    JENIS_KEL = [('L', 'Laki-laki'), ('P', 'Perempuan')]
    PENDIDIKAN = [('SMA', 'SMA/Sederajat'), ('D3', 'D3'), ('S1', 'S1'), ('S2', 'S2')]

    sso_user_id = models.IntegerField(null=True, blank=True)
    nip = models.CharField(max_length=30, blank=True)
    nip_yayasan = models.CharField(max_length=30, blank=True, db_index=True)
    nik = models.CharField(max_length=20, blank=True)
    nama_lengkap = models.CharField(max_length=150)
    jenis_kelamin = models.CharField(max_length=1, choices=JENIS_KEL, blank=True)
    tempat_lahir = models.CharField(max_length=100, blank=True)
    tgl_lahir = models.DateField(null=True, blank=True)
    pendidikan_terakhir = models.CharField(max_length=5, choices=PENDIDIKAN, blank=True)
    no_hp = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    unit_kerja_id = models.IntegerField(null=True, blank=True)
    jabatan = models.CharField(max_length=100, blank=True, help_text='Jabatan/jobdesk sehari-hari, BUKAN jabatan struktural (lihat JabatanStruktural/PejabatStruktural)')
    jenis_kepegawaian_id = models.IntegerField(null=True, blank=True)
    status_kepegawaian_id = models.IntegerField(null=True, blank=True)
    golongan_id = models.IntegerField(null=True, blank=True)
    tgl_mulai_kerja = models.DateField(null=True, blank=True)
    nama_bank = models.CharField(max_length=50, blank=True)
    no_rekening = models.CharField(max_length=30, blank=True)
    atas_nama_rekening = models.CharField(max_length=150, blank=True)
    foto = models.ImageField(upload_to='tendik/foto/', null=True, blank=True, storage=simda_media_storage)
    is_active = models.BooleanField(default=True)
    tgl_dibuat = models.DateTimeField(auto_now_add=True)
    tgl_diperbarui = models.DateTimeField(auto_now=True)
    agama_id = models.IntegerField(null=True, blank=True)
    status_pernikahan = models.CharField(max_length=20, blank=True)
    alamat_domisili = models.TextField(blank=True)
    provinsi_domisili_id = models.IntegerField(null=True, blank=True)
    kabupaten_domisili_id = models.IntegerField(null=True, blank=True)
    kode_pos = models.CharField(max_length=5, blank=True)
    bidang_keahlian = models.CharField(max_length=150, blank=True)
    no_sk_pengangkatan = models.CharField(max_length=100, blank=True)
    tgl_sk_pengangkatan = models.DateField(null=True, blank=True)
    npwp = models.CharField(max_length=20, blank=True)

    # Field yang boleh diedit tendik sendiri lewat halaman "Riwayat Saya"
    # (2026-08-04) -- mirror SELF_SERVICE_FIELDS milik DataDosen. Field
    # kepegawaian/struktural (nip/nip_yayasan/unit_kerja_id/jabatan/
    # jenis_kepegawaian_id/status_kepegawaian_id/golongan_id/
    # tgl_mulai_kerja/nama_bank/no_rekening/atas_nama_rekening/
    # no_sk_pengangkatan/tgl_sk_pengangkatan/is_active/pendidikan_terakhir)
    # SENGAJA TIDAK diikutkan -- tetap admin-only lewat Kelola Data
    # Tendik, sama seperti field ADMIN/HR milik DataDosen.
    SELF_SERVICE_FIELDS = [
        'nik', 'nama_lengkap', 'jenis_kelamin', 'tempat_lahir', 'tgl_lahir',
        'no_hp', 'email', 'agama_id', 'status_pernikahan', 'alamat_domisili',
        'provinsi_domisili_id', 'kabupaten_domisili_id', 'kode_pos',
        'bidang_keahlian', 'foto', 'npwp',
    ]

    class Meta:
        managed = False
        db_table = 'master"."data_tendik'
        verbose_name = 'Data Tendik (SIMDA)'
        verbose_name_plural = 'Data Tendik (SIMDA)'

    def __str__(self):
        return self.nama_lengkap

    @property
    def unit_kerja_nama(self):
        if not self.unit_kerja_id:
            return ''
        uk = UnitKerja.objects.using('simda').filter(id=self.unit_kerja_id).first()
        return uk.nama if uk else ''

    @property
    def jenis_kepegawaian_nama(self):
        if not self.jenis_kepegawaian_id:
            return ''
        jk = JenisKepegawaianPublik.objects.using('simda').filter(id=self.jenis_kepegawaian_id).first()
        return jk.nama if jk else ''

    @property
    def status_kepegawaian_nama(self):
        if not self.status_kepegawaian_id:
            return ''
        sk = StatusKepegawaianPublik.objects.using('simda').filter(id=self.status_kepegawaian_id).first()
        return sk.nama if sk else ''

    @property
    def golongan_nama(self):
        if not self.golongan_id:
            return ''
        g = GolonganPublik.objects.using('simda').filter(id=self.golongan_id).first()
        return f'{g.kode} ({g.pangkat})' if g else ''


class RiwayatPendidikanTendik(models.Model):
    """Riwayat pendidikan Tendik -- mirror pola RiwayatPendidikanDosen,
    FK ke DataTendik (bukan ke accounts.User) supaya bisa diisi admin
    lewat "Kelola Data Tendik" independen dari status akun login, lihat
    tambah_tabel_riwayat_tendik.sql (repo SIMDA) untuk skema tabelnya."""
    JENJANG = [('SMA', 'SMA/Sederajat'), ('D3', 'D3'), ('S1', 'S1'), ('S2', 'S2')]

    tendik = models.ForeignKey(DataTendik, on_delete=models.DO_NOTHING,
                                related_name='riwayat_pendidikan', db_column='tendik_id')
    jenjang = models.CharField(max_length=5, choices=JENJANG)
    institusi = models.CharField(max_length=200)
    jurusan = models.CharField(max_length=150, blank=True)
    tahun_masuk = models.IntegerField(null=True, blank=True)
    tahun_lulus = models.IntegerField(null=True, blank=True)
    no_ijazah = models.CharField(max_length=50, blank=True)
    file_ijazah = models.FileField(upload_to='tendik/ijazah/', null=True, blank=True,
                                    validators=[validate_file_size], storage=simda_media_storage)
    keterangan = models.TextField(blank=True)
    tgl_dibuat = models.DateTimeField(auto_now_add=True)
    tgl_diperbarui = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'master"."riwayat_pendidikan_tendik'
        verbose_name = 'Riwayat Pendidikan Tendik (SIMDA)'
        verbose_name_plural = 'Riwayat Pendidikan Tendik (SIMDA)'
        ordering = ['-tahun_lulus']

    def __str__(self):
        return f'{self.jenjang} - {self.institusi}'


class RiwayatPelatihanTendik(models.Model):
    """Riwayat pelatihan/diklat Tendik -- mirror profil.Diklat (dosen),
    disederhanakan (tanpa field periode akademik yang tidak relevan
    untuk tendik), tapi FK ke DataTendik (SIMDA) bukan ke accounts.User,
    sama alasannya dengan RiwayatPendidikanTendik."""
    TINGKAT = [
        ('Lokal', 'Lokal'), ('Regional', 'Regional'),
        ('Nasional', 'Nasional'), ('Internasional', 'Internasional'),
    ]

    tendik = models.ForeignKey(DataTendik, on_delete=models.DO_NOTHING,
                                related_name='riwayat_pelatihan', db_column='tendik_id')
    nama_pelatihan = models.CharField(max_length=200)
    penyelenggara = models.CharField(max_length=200)
    tingkat = models.CharField(max_length=15, choices=TINGKAT)
    jumlah_jam = models.IntegerField(null=True, blank=True)
    no_sertifikat = models.CharField(max_length=100, blank=True)
    tanggal_mulai = models.DateField(null=True, blank=True)
    tanggal_selesai = models.DateField(null=True, blank=True)
    file_sertifikat = models.FileField(upload_to='tendik/pelatihan/', null=True, blank=True,
                                        validators=[validate_file_size], storage=simda_media_storage)
    keterangan = models.TextField(blank=True)
    tgl_dibuat = models.DateTimeField(auto_now_add=True)
    tgl_diperbarui = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'master"."riwayat_pelatihan_tendik'
        verbose_name = 'Riwayat Pelatihan Tendik (SIMDA)'
        verbose_name_plural = 'Riwayat Pelatihan Tendik (SIMDA)'
        ordering = ['-tanggal_mulai']

    def __str__(self):
        return self.nama_pelatihan


class RiwayatPrestasiTendik(models.Model):
    """Riwayat prestasi/penghargaan Tendik -- mirip semangat
    penunjang.Penghargaan (dosen), disederhanakan, FK ke DataTendik
    (SIMDA) bukan ke accounts.User, sama alasannya dengan 2 model
    riwayat tendik lainnya."""
    TINGKAT = [
        ('Lokal', 'Lokal'), ('Regional', 'Regional'),
        ('Nasional', 'Nasional'), ('Internasional', 'Internasional'),
    ]

    tendik = models.ForeignKey(DataTendik, on_delete=models.DO_NOTHING,
                                related_name='riwayat_prestasi', db_column='tendik_id')
    nama_prestasi = models.CharField(max_length=200)
    pemberi_penghargaan = models.CharField(max_length=200, blank=True)
    tingkat = models.CharField(max_length=15, choices=TINGKAT)
    tahun = models.IntegerField(null=True, blank=True)
    no_sertifikat = models.CharField(max_length=100, blank=True)
    file_bukti = models.FileField(upload_to='tendik/prestasi/', null=True, blank=True,
                                   validators=[validate_file_size], storage=simda_media_storage)
    keterangan = models.TextField(blank=True)
    tgl_dibuat = models.DateTimeField(auto_now_add=True)
    tgl_diperbarui = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'master"."riwayat_prestasi_tendik'
        verbose_name = 'Riwayat Prestasi Tendik (SIMDA)'
        verbose_name_plural = 'Riwayat Prestasi Tendik (SIMDA)'
        ordering = ['-tahun']

    def __str__(self):
        return self.nama_prestasi


class JabatanStruktural(models.Model):
    """Read-only, sumbernya master.jabatan_struktural (tabel mentah --
    bukan data pribadi/sensitif, sama seperti master.mata_kuliah, jadi
    tidak perlu view tersaring). Dipakai untuk cari nama jabatan (mis.
    "Rektor") lewat PejabatStruktural -- lihat
    tambah_akses_pejabat_struktural.sql (repo SIMDA) untuk grant-nya."""
    LINGKUP = [
        ('universitas', 'Universitas'), ('fakultas', 'Fakultas'),
        ('prodi', 'Program Studi'), ('unit', 'Unit Kerja'),
    ]

    kode = models.CharField(max_length=20, unique=True)
    nama = models.CharField(max_length=100)
    singkatan = models.CharField(max_length=20, blank=True)
    level = models.IntegerField(help_text='1=Rektorat, 2=Dekan, 3=Kaprodi, 4=Kepala Unit')
    lingkup = models.CharField(max_length=20, choices=LINGKUP)
    status = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'master"."jabatan_struktural'
        verbose_name = 'Jabatan Struktural (SIMDA)'
        verbose_name_plural = 'Jabatan Struktural (SIMDA)'
        ordering = ['level']

    def __str__(self):
        return self.nama


class PejabatStruktural(models.Model):
    """Read-only, sumbernya master.pejabat_struktural. Dipakai untuk
    mengambil otomatis nama+NIP+gambar tanda tangan pejabat aktif (mis.
    Rektor) untuk blok tanda tangan di laporan resmi (lihat
    presensi/laporan_serdos.py). `tendik` sekarang FK penuh ke DataTendik
    (sebelumnya cuma id mentah sebelum DataTendik di-mirror ke SIKD)."""
    jabatan = models.ForeignKey(JabatanStruktural, on_delete=models.DO_NOTHING, related_name='pejabat')
    dosen = models.ForeignKey(
        DataDosen, on_delete=models.DO_NOTHING, null=True, blank=True, related_name='jabatan_struktural',
    )
    tendik = models.ForeignKey(
        DataTendik, on_delete=models.DO_NOTHING, null=True, blank=True, related_name='jabatan_struktural',
    )
    kode_fakultas = models.CharField(max_length=10, blank=True)
    kode_prodi = models.CharField(max_length=10, blank=True)
    tgl_mulai = models.DateField()
    tgl_selesai = models.DateField(null=True, blank=True)
    is_aktif = models.BooleanField(default=True)
    file_ttd = models.ImageField(
        upload_to='pejabat/ttd/', null=True, blank=True, storage=simda_media_storage,
        verbose_name='File Tanda Tangan',
    )
    lebar_ttd = models.IntegerField(default=60, verbose_name='Lebar TTD (mm)')
    tinggi_ttd = models.IntegerField(default=25, verbose_name='Tinggi TTD (mm)')

    class Meta:
        managed = False
        db_table = 'master"."pejabat_struktural'
        verbose_name = 'Pejabat Struktural (SIMDA)'
        verbose_name_plural = 'Pejabat Struktural (SIMDA)'
        ordering = ['jabatan__level', '-tgl_mulai']

    def __str__(self):
        if self.dosen:
            nama = self.dosen.nama_lengkap
        elif self.tendik:
            nama = self.tendik.nama_lengkap
        else:
            nama = 'tidak diketahui'
        return f'{self.jabatan.nama} — {nama}'
