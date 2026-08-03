from unittest.mock import patch

from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User


class TambahBkdAksesTest(TestCase):
    """tambah_bkd -- lewat resolve_target_user_tambah() (sama pola dengan
    profil/tests.py::TambahJabfungAksesTest). Sejak 2026-08-03 sore:
    menambahkan Laporan BKD ATAS NAMA dosen lain cuma boleh admin/
    operator, dekan/kaprodi fakultas/prodi sendiri TIDAK LAGI boleh.
    SIMDA di-mock (get_simda_dosen_or_none) -- yang diuji murni gerbang
    aksesnya."""

    def setUp(self):
        self.dosen_ft = User.objects.create_user(
            username="dosen_ft_bkd", password="testpass123", role="dosen",
            nidn="8800000301", kode_fakultas="FT", kode_prodi="TI",
        )
        self.dekan_ft = User.objects.create_user(
            username="dekan_ft_bkd", password="testpass123", role="dekan",
            kode_fakultas="FT",
        )
        self.operator_ft = User.objects.create_user(
            username="operator_ft_bkd", password="testpass123", role="operator",
            kode_fakultas="FT",
        )
        self.client = Client()

    def _post(self, user, dosen_id=None):
        self.client.login(username=user.username, password="testpass123")
        data = {"periode_id": "1"}
        if dosen_id is not None:
            data["dosen_id"] = dosen_id
        return self.client.post(reverse("kinerja:tambah_bkd"), data)

    @patch("kinerja.views.get_simda_dosen_or_none")
    def test_dekan_fakultas_sama_ditolak_untuk_dosen_lain(self, mock_profil_fn):
        self._post(self.dekan_ft, self.dosen_ft.id)
        mock_profil_fn.assert_not_called()

    @patch("kinerja.views.get_simda_dosen_or_none")
    def test_operator_fakultas_sama_lolos_gerbang_akses(self, mock_profil_fn):
        mock_profil_fn.return_value = None
        self._post(self.operator_ft, self.dosen_ft.id)
        mock_profil_fn.assert_called_once_with(self.dosen_ft)

    @patch("kinerja.views.get_simda_dosen_or_none")
    def test_dekan_tetap_lolos_gerbang_untuk_diri_sendiri(self, mock_profil_fn):
        mock_profil_fn.return_value = None
        self._post(self.dekan_ft)
        mock_profil_fn.assert_called_once_with(self.dekan_ft)
