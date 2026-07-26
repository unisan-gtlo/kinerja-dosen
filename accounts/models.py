from django.contrib.auth.models import AbstractUser
from django.db import models


ROLE_CHOICES = [
    ('admin', 'Administrator'),
    ('rektorat', 'Rektorat'),
    ('biro', 'Biro/Lembaga'),
    ('dekan', 'Dekan'),
    ('wadek', 'Wakil Dekan'),
    ('operator', 'Operator Fakultas'),
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
        return self.role in ['dekan', 'wadek', 'operator']

    @property
    def is_kaprodi_level(self):
        return self.role in ['kaprodi', 'sekprodi']

    @property
    def is_dosen(self):
        return self.role == 'dosen'

    @property
    def can_view_all(self):
        return self.role in ['admin', 'rektorat', 'biro']

    @property
    def can_export(self):
        return self.role in ['admin', 'rektorat', 'biro', 'dekan', 'wadek', 'kaprodi', 'sekprodi', 'operator']

    def dapat_kelola(self, target_user):
        """True kalau self boleh kelola (edit/hapus akun & data kinerja)
        target_user. Admin: semua dosen. Dekan/Wadek/Operator: dosen
        se-fakultas (satu operator cukup untuk satu fakultas). Kaprodi/
        Sekprodi: dosen se-prodi. Rektorat/Biro SENGAJA tidak diikutkan --
        baca data saja (dashboard/rekap/laporan tetap lihat semua), tidak
        boleh edit/kelola akun. Selain itu, cuma boleh kelola diri sendiri."""
        if self.id == target_user.id:
            return True
        if self.role == 'admin':
            return True
        if self.role in ['dekan', 'wadek', 'operator']:
            return bool(self.kode_fakultas) and self.kode_fakultas == target_user.kode_fakultas
        if self.role in ['kaprodi', 'sekprodi']:
            return bool(self.kode_prodi) and self.kode_prodi == target_user.kode_prodi
        return False
    def get_role_display_id(self):
        role_labels = {
        'admin': 'Administrator',
        'rektorat': 'Rektorat',
        'biro': 'Biro/Lembaga',
        'dekan': 'Dekan',
        'wadek': 'Wakil Dekan',
        'operator': 'Operator Fakultas',
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