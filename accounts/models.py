from django.contrib.auth.models import AbstractUser
from django.db import models


ROLE_CHOICES = [
    ('admin', 'Administrator'),
    ('rektorat', 'Rektorat'),
    ('biro', 'Biro/Lembaga'),
    ('dekan', 'Dekan'),
    ('wadek', 'Wakil Dekan'),
    ('kaprodi', 'Ketua Program Studi'),
    ('sekprodi', 'Sekretaris Prodi'),
    ('tendik', 'Tendik'),
    ('dosen', 'Dosen'),
]

class User(AbstractUser):
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='dosen')
    nidn = models.CharField(max_length=20, blank=True, null=True)
    nip_yayasan = models.CharField(max_length=30, blank=True, null=True)
    kode_fakultas = models.CharField(max_length=10, blank=True, null=True)
    kode_prodi = models.CharField(max_length=10, blank=True, null=True)
    no_hp = models.CharField(max_length=20, blank=True, null=True)
    status_akun = models.CharField(
        max_length=10,
        choices=[('aktif', 'Aktif'), ('nonaktif', 'Nonaktif')],
        default='aktif'
    )
    status_kepegawaian = models.CharField(
    max_length=20,
    choices=[
        ('Aktif', 'Aktif'),
        ('Tugas Belajar', 'Tugas Belajar'),
        ('Lanjut Studi', 'Lanjut Studi'),
        ('Keluar', 'Keluar'),
        ('Meninggal', 'Meninggal'),
    ],
    default='Aktif',
    blank=True, null=True
    )

    class Meta:
        verbose_name = 'Pengguna'
        verbose_name_plural = 'Pengguna'

    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_rektorat(self):
        return self.role in ['rektorat', 'biro']

    @property
    def is_dekan_level(self):
        return self.role in ['dekan', 'wadek']

    @property
    def is_kaprodi_level(self):
        return self.role in ['kaprodi', 'sekprodi', 'operator']

    @property
    def is_dosen(self):
        return self.role == 'dosen'

    @property
    def can_view_all(self):
        return self.role in ['admin', 'rektorat', 'biro']

    @property
    def can_export(self):
        return self.role in ['admin', 'rektorat', 'biro', 'dekan', 'wadek', 'kaprodi']
    def get_role_display_id(self):
        role_labels = {
        'admin': 'Administrator',
        'rektorat': 'Rektorat',
        'biro': 'Biro/Lembaga',
        'dekan': 'Dekan',
        'wadek': 'Wakil Dekan',
        'kaprodi': 'Kepala Program Studi',
        'sekprodi': 'Sekretaris Prodi',
        'tendik': 'Tendik',
        'dosen': 'Dosen',
    }
        return role_labels.get(self.role, self.role)    

class LogAktivitas(models.Model):
    JENIS_CHOICES = [
        ('login_berhasil', 'Login Berhasil'),
        ('login_gagal', 'Login Gagal'),
        ('login_nonaktif', 'Login Ditolak (Nonaktif)'),
        ('captcha_salah', 'CAPTCHA Salah'),
        ('logout', 'Logout'),
    ]
    username = models.CharField(max_length=150)
    nama = models.CharField(max_length=200, blank=True)
    role = models.CharField(max_length=20, blank=True)
    jenis = models.CharField(max_length=20, choices=JENIS_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    waktu = models.DateTimeField(auto_now_add=True)
    keterangan = models.TextField(blank=True)

    class Meta:
        ordering = ['-waktu']
        verbose_name = 'Log Aktivitas'
        verbose_name_plural = 'Log Aktivitas'

    def __str__(self):
        return f'{self.waktu} | {self.jenis} | {self.username} | {self.ip_address}'