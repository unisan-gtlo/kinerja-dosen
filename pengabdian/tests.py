from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User
from .models import Pengabdian


class TambahPengabdianAksesTest(TestCase):
    """tambah_pengabdian (dan tambah_pembicara/tambah_jurnal/
    tambah_jabatan di app ini, pola identik) -- lihat
    pendidikan/tests.py::TambahOrasiIlmiahAksesTest untuk riwayat
    lengkap 2 tahap pembatasan. Sejak 2026-08-03 sore: menambahkan data
    ATAS NAMA dosen lain cuma boleh admin/operator, dekan/kaprodi
    fakultas/prodi sendiri TIDAK LAGI boleh. Data diri sendiri tetap
    boleh untuk siapa pun."""

    def setUp(self):
        self.dosen_ft = User.objects.create_user(
            username="dosen_ft_pengabdian", password="testpass123", role="dosen",
            kode_fakultas="FT", kode_prodi="TI",
        )
        self.dekan_ft = User.objects.create_user(
            username="dekan_ft_pengabdian", password="testpass123", role="dekan",
            kode_fakultas="FT",
        )
        self.dekan_feb = User.objects.create_user(
            username="dekan_feb_pengabdian", password="testpass123", role="dekan",
            kode_fakultas="FEB",
        )
        self.operator_ft = User.objects.create_user(
            username="operator_ft_pengabdian", password="testpass123", role="operator",
            kode_fakultas="FT",
        )
        self.rektorat = User.objects.create_user(
            username="rektorat_pengabdian", password="testpass123", role="rektorat",
        )
        self.client = Client()

    def _post(self, user, dosen_id=None):
        self.client.force_login(user)
        # tahun_usulan/tahun_pelaksanaan wajib -- IntegerField() NOT NULL
        # tanpa default di Pengabdian. Sebelum fix force_login (lihat
        # CLAUDE.md), test ini tidak pernah benar-benar mencapai
        # Pengabdian.objects.create(), jadi celah data test ini baru
        # ketahuan sekarang.
        data = {
            "judul_kegiatan": "Contoh Pengabdian",
            "tahun_usulan": "2024", "tahun_pelaksanaan": "2024",
        }
        if dosen_id is not None:
            data["dosen_id"] = dosen_id
        return self.client.post(reverse("pengabdian:tambah_pengabdian"), data)

    def test_dekan_beda_fakultas_ditolak(self):
        self._post(self.dekan_feb, self.dosen_ft.id)
        self.assertEqual(Pengabdian.objects.filter(user=self.dosen_ft).count(), 0)

    def test_rektorat_read_only_ditolak(self):
        self._post(self.rektorat, self.dosen_ft.id)
        self.assertEqual(Pengabdian.objects.filter(user=self.dosen_ft).count(), 0)

    def test_dekan_fakultas_sama_ditolak_untuk_dosen_lain(self):
        self._post(self.dekan_ft, self.dosen_ft.id)
        self.assertEqual(Pengabdian.objects.filter(user=self.dosen_ft).count(), 0)

    def test_operator_fakultas_sama_diterima(self):
        self._post(self.operator_ft, self.dosen_ft.id)
        self.assertEqual(Pengabdian.objects.filter(user=self.dosen_ft).count(), 1)

    def test_dekan_tetap_bisa_tambah_untuk_diri_sendiri(self):
        self._post(self.dekan_ft)
        self.assertEqual(Pengabdian.objects.filter(user=self.dekan_ft).count(), 1)


class RedirectMempertahankanDosenIdTest(TestCase):
    """2026-08-07: lihat pendidikan/tests.py::RedirectMempertahankanDosenIdTest
    untuk penjelasan lengkap bug & fix (redirect_ke). Representatif untuk
    tambah_pengabdian/edit_pengabdian/hapus_pengabdian di app ini."""

    def setUp(self):
        self.dosen_ft = User.objects.create_user(
            username="dosen_ft_redirect_pengabdian", password="testpass123", role="dosen",
            kode_fakultas="FT", kode_prodi="TI",
        )
        self.admin = User.objects.create_user(
            username="admin_redirect_pengabdian", password="testpass123", role="admin",
        )
        self.client = Client()
        self.client.force_login(self.admin)

    def test_tambah_untuk_dosen_lain_redirect_bawa_dosen_id(self):
        resp = self.client.post(reverse("pengabdian:tambah_pengabdian"), {
            "judul_kegiatan": "Contoh Pengabdian",
            "tahun_usulan": "2024", "tahun_pelaksanaan": "2024",
            "dosen_id": self.dosen_ft.id,
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn(f"?dosen_id={self.dosen_ft.id}", resp.url)

    def test_edit_untuk_dosen_lain_redirect_bawa_dosen_id(self):
        obj = Pengabdian.objects.create(
            user=self.dosen_ft, judul_kegiatan="Lama",
            tahun_usulan=2023, tahun_pelaksanaan=2023,
        )
        resp = self.client.post(reverse("pengabdian:edit_pengabdian", args=[obj.id]), {
            "judul_kegiatan": "Baru", "tahun_usulan": "2024", "tahun_pelaksanaan": "2024",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn(f"?dosen_id={self.dosen_ft.id}", resp.url)

    def test_hapus_untuk_dosen_lain_redirect_bawa_dosen_id(self):
        obj = Pengabdian.objects.create(
            user=self.dosen_ft, judul_kegiatan="Lama",
            tahun_usulan=2023, tahun_pelaksanaan=2023,
        )
        resp = self.client.post(reverse("pengabdian:hapus_pengabdian", args=[obj.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(f"?dosen_id={self.dosen_ft.id}", resp.url)
