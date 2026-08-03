from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User
from .models import OrasiIlmiah


class TambahOrasiIlmiahAksesTest(TestCase):
    """Bug fix per 2026-08-03: tambah_orasi_ilmiah (dan 6 tambah_* lain di
    app ini) sebelumnya tidak mengecek dapat_kelola() sebelum menyimpan --
    siapa pun di 8-role list bisa membuat data untuk dosen mana pun,
    termasuk di luar fakultas/prodinya, dan rektorat/biro (read-only)
    bisa ikut menulis. Sekarang tambah_orasi_ilmiah (representatif --
    pola dapat_kelola-nya identik di 7 tambah_* app ini) harus menolak
    kasus tidak berwenang dan tetap menerima kasus yang berwenang."""

    def setUp(self):
        self.dosen_ft = User.objects.create_user(
            username="dosen_ft_pendidikan", password="testpass123", role="dosen",
            kode_fakultas="FT", kode_prodi="TI",
        )
        self.dekan_ft = User.objects.create_user(
            username="dekan_ft_pendidikan", password="testpass123", role="dekan",
            kode_fakultas="FT",
        )
        self.dekan_feb = User.objects.create_user(
            username="dekan_feb_pendidikan", password="testpass123", role="dekan",
            kode_fakultas="FEB",
        )
        self.rektorat = User.objects.create_user(
            username="rektorat_pendidikan", password="testpass123", role="rektorat",
        )
        self.admin = User.objects.create_user(
            username="admin_pendidikan", password="testpass123", role="admin",
        )
        self.client = Client()

    def _post(self, user):
        self.client.login(username=user.username, password="testpass123")
        return self.client.post(
            reverse("pendidikan:tambah_orasi_ilmiah"),
            {"dosen_id": self.dosen_ft.id, "judul_orasi": "Contoh Orasi"},
        )

    def test_dekan_beda_fakultas_ditolak(self):
        self._post(self.dekan_feb)
        self.assertEqual(OrasiIlmiah.objects.filter(user=self.dosen_ft).count(), 0)

    def test_rektorat_read_only_ditolak(self):
        self._post(self.rektorat)
        self.assertEqual(OrasiIlmiah.objects.filter(user=self.dosen_ft).count(), 0)

    def test_dekan_fakultas_sama_diterima(self):
        self._post(self.dekan_ft)
        self.assertEqual(OrasiIlmiah.objects.filter(user=self.dosen_ft).count(), 1)

    def test_admin_selalu_diterima(self):
        self._post(self.admin)
        self.assertEqual(OrasiIlmiah.objects.filter(user=self.dosen_ft).count(), 1)
