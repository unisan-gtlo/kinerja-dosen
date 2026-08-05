from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User
from .models import Beasiswa


class TambahBeasiswaAksesTest(TestCase):
    """tambah_beasiswa (dan tambah_kesejahteraan/tambah_tunjangan di
    app ini, pola identik) -- lihat
    pendidikan/tests.py::TambahOrasiIlmiahAksesTest untuk riwayat
    lengkap 2 tahap pembatasan. Sejak 2026-08-03 sore: menambahkan data
    ATAS NAMA dosen lain cuma boleh admin/operator, dekan/kaprodi
    fakultas/prodi sendiri TIDAK LAGI boleh. Data diri sendiri tetap
    boleh untuk siapa pun."""

    def setUp(self):
        self.dosen_ft = User.objects.create_user(
            username="dosen_ft_reward", password="testpass123", role="dosen",
            kode_fakultas="FT", kode_prodi="TI",
        )
        self.dekan_ft = User.objects.create_user(
            username="dekan_ft_reward", password="testpass123", role="dekan",
            kode_fakultas="FT",
        )
        self.dekan_feb = User.objects.create_user(
            username="dekan_feb_reward", password="testpass123", role="dekan",
            kode_fakultas="FEB",
        )
        self.operator_ft = User.objects.create_user(
            username="operator_ft_reward", password="testpass123", role="operator",
            kode_fakultas="FT",
        )
        self.rektorat = User.objects.create_user(
            username="rektorat_reward", password="testpass123", role="rektorat",
        )
        self.client = Client()

    def _post(self, user, dosen_id=None):
        self.client.force_login(user)
        # tahun_mulai wajib -- IntegerField() NOT NULL tanpa default di
        # Beasiswa. Sebelum fix force_login (lihat CLAUDE.md), test ini
        # tidak pernah benar-benar mencapai Beasiswa.objects.create(),
        # jadi celah data test ini baru ketahuan sekarang.
        data = {"nama_beasiswa": "Contoh Beasiswa", "tahun_mulai": "2024"}
        if dosen_id is not None:
            data["dosen_id"] = dosen_id
        return self.client.post(reverse("reward:tambah_beasiswa"), data)

    def test_dekan_beda_fakultas_ditolak(self):
        self._post(self.dekan_feb, self.dosen_ft.id)
        self.assertEqual(Beasiswa.objects.filter(user=self.dosen_ft).count(), 0)

    def test_rektorat_read_only_ditolak(self):
        self._post(self.rektorat, self.dosen_ft.id)
        self.assertEqual(Beasiswa.objects.filter(user=self.dosen_ft).count(), 0)

    def test_dekan_fakultas_sama_ditolak_untuk_dosen_lain(self):
        self._post(self.dekan_ft, self.dosen_ft.id)
        self.assertEqual(Beasiswa.objects.filter(user=self.dosen_ft).count(), 0)

    def test_operator_fakultas_sama_diterima(self):
        self._post(self.operator_ft, self.dosen_ft.id)
        self.assertEqual(Beasiswa.objects.filter(user=self.dosen_ft).count(), 1)

    def test_dekan_tetap_bisa_tambah_untuk_diri_sendiri(self):
        self._post(self.dekan_ft)
        self.assertEqual(Beasiswa.objects.filter(user=self.dekan_ft).count(), 1)
