from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User
from .models import OrasiIlmiah


class TambahOrasiIlmiahAksesTest(TestCase):
    """tambah_orasi_ilmiah (dan 6 tambah_* lain di app ini, pola identik)
    -- riwayat 2 tahap:
    (1) 2026-08-03 pagi: sebelumnya tidak mengecek dapat_kelola() sama
        sekali sebelum menyimpan -- siapa pun di 8-role list bisa
        membuat data untuk dosen mana pun, termasuk rektorat/biro
        (read-only) dan dekan/kaprodi di luar fakultas/prodinya.
    (2) 2026-08-03 sore: dipersempit LEBIH LANJUT lewat
        bisa_tambah_tridarma() -- menambahkan data ATAS NAMA dosen lain
        sekarang cuma boleh admin/operator; dekan/wadek/kaprodi/sekprodi/
        rektorat/biro TIDAK LAGI boleh sama sekali (sebelumnya dekan/
        kaprodi FAKULTAS/PRODI SENDIRI masih boleh lewat dapat_kelola()).
        Data diri sendiri (self-service) tetap boleh untuk siapa pun."""

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
        self.operator_ft = User.objects.create_user(
            username="operator_ft_pendidikan", password="testpass123", role="operator",
            kode_fakultas="FT",
        )
        self.rektorat = User.objects.create_user(
            username="rektorat_pendidikan", password="testpass123", role="rektorat",
        )
        self.admin = User.objects.create_user(
            username="admin_pendidikan", password="testpass123", role="admin",
        )
        self.client = Client()

    def _post(self, user, dosen_id=None):
        self.client.force_login(user)
        # tanggal wajib diisi -- OrasiIlmiah.tanggal DateField() NOT NULL
        # tanpa default. Sebelum fix force_login (lihat CLAUDE.md), test
        # ini tidak pernah benar-benar mencapai OrasiIlmiah.objects.create()
        # (client.login() sudah gagal duluan karena django-axes), jadi
        # celah data test ini baru ketahuan sekarang.
        data = {"judul_orasi": "Contoh Orasi", "tanggal": "2024-01-15"}
        if dosen_id is not None:
            data["dosen_id"] = dosen_id
        return self.client.post(reverse("pendidikan:tambah_orasi_ilmiah"), data)

    def test_dekan_beda_fakultas_ditolak(self):
        self._post(self.dekan_feb, self.dosen_ft.id)
        self.assertEqual(OrasiIlmiah.objects.filter(user=self.dosen_ft).count(), 0)

    def test_rektorat_read_only_ditolak(self):
        self._post(self.rektorat, self.dosen_ft.id)
        self.assertEqual(OrasiIlmiah.objects.filter(user=self.dosen_ft).count(), 0)

    def test_dekan_fakultas_sama_ditolak_untuk_dosen_lain(self):
        """Sejak dipersempit -- dekan fakultas SAMA pun tidak lagi boleh
        menambahkan data untuk dosen lain, hanya admin/operator."""
        self._post(self.dekan_ft, self.dosen_ft.id)
        self.assertEqual(OrasiIlmiah.objects.filter(user=self.dosen_ft).count(), 0)

    def test_operator_fakultas_sama_diterima(self):
        self._post(self.operator_ft, self.dosen_ft.id)
        self.assertEqual(OrasiIlmiah.objects.filter(user=self.dosen_ft).count(), 1)

    def test_admin_selalu_diterima(self):
        self._post(self.admin, self.dosen_ft.id)
        self.assertEqual(OrasiIlmiah.objects.filter(user=self.dosen_ft).count(), 1)

    def test_dekan_tetap_bisa_tambah_untuk_diri_sendiri(self):
        self._post(self.dekan_ft)
        self.assertEqual(OrasiIlmiah.objects.filter(user=self.dekan_ft).count(), 1)
