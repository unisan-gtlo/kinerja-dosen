from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User
from .models import Penelitian


class TambahPenelitianAksesTest(TestCase):
    """Bug fix per 2026-08-03: tambah_penelitian (dan tambah_publikasi/
    tambah_paten di app ini) sebelumnya tidak mengecek dapat_kelola()
    sebelum menyimpan -- lihat pendidikan/tests.py::TambahOrasiIlmiahAksesTest
    untuk penjelasan lengkap, pola bug & fix-nya identik di app ini."""

    def setUp(self):
        self.dosen_ft = User.objects.create_user(
            username="dosen_ft_penelitian", password="testpass123", role="dosen",
            kode_fakultas="FT", kode_prodi="TI",
        )
        self.dekan_ft = User.objects.create_user(
            username="dekan_ft_penelitian", password="testpass123", role="dekan",
            kode_fakultas="FT",
        )
        self.dekan_feb = User.objects.create_user(
            username="dekan_feb_penelitian", password="testpass123", role="dekan",
            kode_fakultas="FEB",
        )
        self.rektorat = User.objects.create_user(
            username="rektorat_penelitian", password="testpass123", role="rektorat",
        )
        self.client = Client()

    def _post(self, user):
        self.client.login(username=user.username, password="testpass123")
        return self.client.post(
            reverse("penelitian:tambah_penelitian"),
            {"dosen_id": self.dosen_ft.id, "judul_kegiatan": "Contoh Penelitian"},
        )

    def test_dekan_beda_fakultas_ditolak(self):
        self._post(self.dekan_feb)
        self.assertEqual(Penelitian.objects.filter(user=self.dosen_ft).count(), 0)

    def test_rektorat_read_only_ditolak(self):
        self._post(self.rektorat)
        self.assertEqual(Penelitian.objects.filter(user=self.dosen_ft).count(), 0)

    def test_dekan_fakultas_sama_diterima(self):
        self._post(self.dekan_ft)
        self.assertEqual(Penelitian.objects.filter(user=self.dosen_ft).count(), 1)
