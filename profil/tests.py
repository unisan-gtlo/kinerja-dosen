from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User
from .models import DokumenLain


class TambahDokumenLainAksesTest(TestCase):
    """Bug fix per 2026-08-03: tambah_dokumen_lain sebelumnya memakai
    _dokumen_target_user() (baca dosen_id dari request.GET) padahal
    dipanggil dari alur POST (mismatch GET/POST membuatnya bisa
    dieksploitasi lewat query string+body sekaligus), dan TIDAK mengecek
    dapat_kelola() sama sekali -- siapa pun di 8-role list bisa membuat
    dokumen untuk dosen mana pun, termasuk di luar fakultas/prodinya, dan
    rektorat/biro (read-only) bisa ikut menulis. Endpoint edit_/hapus_
    dokumen_lain di app ini sudah benar sejak awal, cuma tambah_ yang
    bolong -- lihat pendidikan/tests.py::TambahOrasiIlmiahAksesTest untuk
    pola bug yang sama di app lain."""

    def setUp(self):
        self.dosen_ft = User.objects.create_user(
            username="dosen_ft_profil", password="testpass123", role="dosen",
            kode_fakultas="FT", kode_prodi="TI",
        )
        self.dekan_ft = User.objects.create_user(
            username="dekan_ft_profil", password="testpass123", role="dekan",
            kode_fakultas="FT",
        )
        self.dekan_feb = User.objects.create_user(
            username="dekan_feb_profil", password="testpass123", role="dekan",
            kode_fakultas="FEB",
        )
        self.rektorat = User.objects.create_user(
            username="rektorat_profil", password="testpass123", role="rektorat",
        )
        self.client = Client()

    def _post(self, user):
        self.client.login(username=user.username, password="testpass123")
        return self.client.post(
            reverse("profil:tambah_dokumen_lain"),
            {
                "dosen_id": self.dosen_ft.id,
                "jenis_dokumen": "lainnya",
                "nama_dokumen": "Contoh Dokumen",
            },
        )

    def test_dekan_beda_fakultas_ditolak(self):
        self._post(self.dekan_feb)
        self.assertEqual(DokumenLain.objects.filter(user=self.dosen_ft).count(), 0)

    def test_rektorat_read_only_ditolak(self):
        self._post(self.rektorat)
        self.assertEqual(DokumenLain.objects.filter(user=self.dosen_ft).count(), 0)

    def test_dekan_fakultas_sama_diterima(self):
        self._post(self.dekan_ft)
        self.assertEqual(DokumenLain.objects.filter(user=self.dosen_ft).count(), 1)

    def test_mismatch_get_post_dosen_id_tetap_ditolak(self):
        """Sebelum fix, dosen_id di GET query string dibaca oleh
        _dokumen_target_user() terlepas dari body POST -- pastikan
        exploit ini sudah tidak berfungsi."""
        self.client.login(username=self.dekan_feb.username, password="testpass123")
        url = reverse("profil:tambah_dokumen_lain") + f"?dosen_id={self.dosen_ft.id}"
        self.client.post(url, {"jenis_dokumen": "lainnya", "nama_dokumen": "Exploit"})
        self.assertEqual(DokumenLain.objects.filter(user=self.dosen_ft).count(), 0)
