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


def validate_file_size(value):
    """Sama seperti sdm.models.validate_file_size di SIMDA -- maks 1 MB,
    supaya konsisten dengan validator di sisi SIMDA."""
    limit_mb = 1
    if value.size > limit_mb * 1024 * 1024:
        raise ValidationError(
            f'Ukuran file maksimal {limit_mb} MB. '
            f'File Anda: {value.size / (1024 * 1024):.2f} MB.'
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
    bidang_keahlian_id = models.IntegerField(null=True, blank=True)
    tgl_mulai_kerja = models.DateField(null=True, blank=True)
    no_sk_pengangkatan = models.CharField(max_length=100, blank=True)
    tgl_sk_pengangkatan = models.DateField(null=True, blank=True)
    id_serdos = models.CharField(max_length=30, blank=True)
    nama_bank = models.CharField(max_length=50, blank=True)
    no_rekening = models.CharField(max_length=30, blank=True)
    atas_nama_rekening = models.CharField(max_length=100, blank=True)
    file_sk_pengangkatan = models.FileField(upload_to='dosen/sk_pengangkatan/', null=True, blank=True)
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
                              validators=[validate_file_size])
    file_ktp = models.FileField(upload_to='dosen/ktp/', null=True, blank=True,
                                 validators=[validate_file_size])
    file_npwp = models.FileField(upload_to='dosen/npwp/', null=True, blank=True,
                                  validators=[validate_file_size])
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
                                validators=[validate_file_size])
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
                                    validators=[validate_file_size])
    url_ijazah = models.URLField(blank=True)
    file_transkrip = models.FileField(upload_to='dosen/transkrip/', null=True, blank=True,
                                       validators=[validate_file_size])
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
                                 validators=[validate_file_size], verbose_name='File BKD')
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
