from unittest.mock import patch

from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User
from .models import DokumenLain


class TambahDokumenLainAksesTest(TestCase):
    """tambah_dokumen_lain -- riwayat 2 tahap (lihat
    pendidikan/tests.py::TambahOrasiIlmiahAksesTest untuk penjelasan
    lengkap pola yang sama di app lain):
    (1) 2026-08-03 pagi: sebelumnya memakai _dokumen_target_user() (baca
        dosen_id dari request.GET) padahal dipanggil dari alur POST
        (mismatch GET/POST bisa dieksploitasi), dan TIDAK mengecek
        dapat_kelola() sama sekali.
    (2) 2026-08-03 sore: dipersempit LEBIH LANJUT lewat
        bisa_tambah_tridarma() -- menambahkan dokumen ATAS NAMA dosen
        lain sekarang cuma boleh admin/operator, dekan/kaprodi fakultas/
        prodi sendiri TIDAK LAGI boleh. Data diri sendiri tetap boleh.
    edit_/hapus_dokumen_lain tidak disentuh sama sekali di app ini."""

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
        self.operator_ft = User.objects.create_user(
            username="operator_ft_profil", password="testpass123", role="operator",
            kode_fakultas="FT",
        )
        self.rektorat = User.objects.create_user(
            username="rektorat_profil", password="testpass123", role="rektorat",
        )
        self.client = Client()

    def _post(self, user, dosen_id=None):
        self.client.login(username=user.username, password="testpass123")
        data = {"jenis_dokumen": "lainnya", "nama_dokumen": "Contoh Dokumen"}
        if dosen_id is not None:
            data["dosen_id"] = dosen_id
        return self.client.post(reverse("profil:tambah_dokumen_lain"), data)

    def test_dekan_beda_fakultas_ditolak(self):
        self._post(self.dekan_feb, self.dosen_ft.id)
        self.assertEqual(DokumenLain.objects.filter(user=self.dosen_ft).count(), 0)

    def test_rektorat_read_only_ditolak(self):
        self._post(self.rektorat, self.dosen_ft.id)
        self.assertEqual(DokumenLain.objects.filter(user=self.dosen_ft).count(), 0)

    def test_dekan_fakultas_sama_ditolak_untuk_dosen_lain(self):
        self._post(self.dekan_ft, self.dosen_ft.id)
        self.assertEqual(DokumenLain.objects.filter(user=self.dosen_ft).count(), 0)

    def test_operator_fakultas_sama_diterima(self):
        self._post(self.operator_ft, self.dosen_ft.id)
        self.assertEqual(DokumenLain.objects.filter(user=self.dosen_ft).count(), 1)

    def test_dekan_tetap_bisa_tambah_untuk_diri_sendiri(self):
        self._post(self.dekan_ft)
        self.assertEqual(DokumenLain.objects.filter(user=self.dekan_ft).count(), 1)

    def test_mismatch_get_post_dosen_id_tetap_ditolak(self):
        """Sebelum fix, dosen_id di GET query string dibaca oleh
        _dokumen_target_user() terlepas dari body POST -- pastikan
        exploit ini sudah tidak berfungsi."""
        self.client.login(username=self.dekan_feb.username, password="testpass123")
        url = reverse("profil:tambah_dokumen_lain") + f"?dosen_id={self.dosen_ft.id}"
        self.client.post(url, {"jenis_dokumen": "lainnya", "nama_dokumen": "Exploit"})
        self.assertEqual(DokumenLain.objects.filter(user=self.dosen_ft).count(), 0)


class TambahJabfungAksesTest(TestCase):
    """tambah_jabfung (dan tambah_pangkat/tambah_pendidikan/tambah_diklat/
    tambah_sertifikasi/tambah_tes di app ini, semuanya lewat
    resolve_target_user_tambah()) -- sama pola dengan
    TambahDokumenLainAksesTest, cuma jalur create-nya beda (lewat
    resolve_target_user_tambah, bukan pengecekan inline). SIMDA di-mock
    (get_simda_dosen_or_none) supaya test tidak perlu koneksi 'simda'
    sungguhan -- yang diuji di sini murni gerbang aksesnya, bukan
    penulisan datanya ke SIMDA."""

    def setUp(self):
        self.dosen_ft = User.objects.create_user(
            username="dosen_ft_jabfung", password="testpass123", role="dosen",
            nidn="8800000201", kode_fakultas="FT", kode_prodi="TI",
        )
        self.dekan_ft = User.objects.create_user(
            username="dekan_ft_jabfung", password="testpass123", role="dekan",
            kode_fakultas="FT",
        )
        self.operator_ft = User.objects.create_user(
            username="operator_ft_jabfung", password="testpass123", role="operator",
            kode_fakultas="FT",
        )
        self.client = Client()

    def _post(self, user, dosen_id=None):
        self.client.login(username=user.username, password="testpass123")
        data = {"jabatan_fungsional_id": "1"}
        if dosen_id is not None:
            data["dosen_id"] = dosen_id
        return self.client.post(reverse("profil:tambah_jabfung"), data)

    @patch("profil.views.get_simda_dosen_or_none")
    def test_dekan_fakultas_sama_ditolak_untuk_dosen_lain(self, mock_profil_fn):
        self._post(self.dekan_ft, self.dosen_ft.id)
        mock_profil_fn.assert_not_called()

    @patch("profil.views.get_simda_dosen_or_none")
    def test_operator_fakultas_sama_lolos_gerbang_akses(self, mock_profil_fn):
        mock_profil_fn.return_value = None
        self._post(self.operator_ft, self.dosen_ft.id)
        mock_profil_fn.assert_called_once_with(self.dosen_ft)

    @patch("profil.views.get_simda_dosen_or_none")
    def test_dekan_tetap_lolos_gerbang_untuk_diri_sendiri(self, mock_profil_fn):
        mock_profil_fn.return_value = None
        self._post(self.dekan_ft)
        mock_profil_fn.assert_called_once_with(self.dekan_ft)
