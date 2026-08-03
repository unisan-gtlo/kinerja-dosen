"""Test untuk simda_dosen -- SIMDA (koneksi 'simda') tidak selalu
tersedia saat test, jadi query ke sana di-mock (pola sama dengan
GetPejabatAktifTest/GetDosenByNidnTest di presensi/tests.py)."""
from unittest.mock import MagicMock, patch

from django.db import DatabaseError
from django.test import TestCase

from accounts.models import User

from .forms import DataTendikForm
from .utils import bisa_tambah_tridarma


class DataTendikFormTest(TestCase):
    """Form Kelola Data Tendik -- dropdown referensi (unit kerja/jenis-
    status kepegawaian/golongan/agama) diisi di __init__ dari SIMDA."""

    @patch("simda_dosen.forms.AgamaPublik")
    @patch("simda_dosen.forms.GolonganPublik")
    @patch("simda_dosen.forms.StatusKepegawaianPublik")
    @patch("simda_dosen.forms.JenisKepegawaianPublik")
    @patch("simda_dosen.forms.UnitKerja")
    def test_dropdown_diisi_dari_referensi_simda(
        self, mock_unit, mock_jenis, mock_status, mock_golongan, mock_agama,
    ):
        mock_unit.objects.using.return_value.filter.return_value.order_by.return_value = [
            MagicMock(id=1, __str__=lambda self: "TU — Tata Usaha"),
        ]
        mock_jenis.objects.using.return_value.all.return_value = [MagicMock(id=2, nama="PNS")]
        mock_status.objects.using.return_value.all.return_value = [MagicMock(id=3, nama="Aktif")]
        mock_golongan.objects.using.return_value.all.return_value = [
            MagicMock(id=4, kode="IIIa", pangkat="Penata Muda"),
        ]
        mock_agama.objects.using.return_value.order_by.return_value = [MagicMock(id=5, nama="Islam")]

        form = DataTendikForm()

        self.assertEqual(len(form.fields["unit_kerja_id"].choices), 2)  # kosong + 1
        self.assertIn((2, "PNS"), form.fields["jenis_kepegawaian_id"].choices)
        self.assertIn((3, "Aktif"), form.fields["status_kepegawaian_id"].choices)
        self.assertIn((5, "Islam"), form.fields["agama_id"].choices)

    @patch("simda_dosen.forms.UnitKerja")
    def test_database_error_fallback_dropdown_kosong_bukan_crash(self, mock_unit):
        # Regresi: kalau akses master.data_tendik/unit_kerja belum
        # di-grant, form Kelola Data Tendik tetap bisa dibuka (dropdown
        # kosong), bukan 500 -- pola sama dengan get_pejabat_aktif.
        mock_unit.objects.using.side_effect = DatabaseError("permission denied")

        form = DataTendikForm()

        self.assertEqual(form.fields["unit_kerja_id"].choices, [("", "---------")])


class KelolaDataTendikViewTest(TestCase):
    """Halaman /simda-dosen/tendik/ -- admin-only. Data tendik tidak
    punya konsep fakultas/prodi untuk discope dapat_kelola seperti
    Kelola User, dan field-nya termasuk data HR sensitif (NIK/rekening/
    NPWP), jadi sengaja dibatasi admin saja."""

    def setUp(self):
        self.admin = User.objects.create_user(username="tendikadmin", password="testpass123", role="admin")
        self.dosen = User.objects.create_user(username="tendikdosen", password="testpass123", role="dosen")

    def test_dosen_biasa_tidak_bisa_akses_daftar(self):
        self.client.force_login(self.dosen)
        resp = self.client.get("/simda-dosen/tendik/")
        self.assertEqual(resp.status_code, 403)

    def test_dosen_biasa_tidak_bisa_akses_tambah(self):
        self.client.force_login(self.dosen)
        resp = self.client.get("/simda-dosen/tendik/tambah/")
        self.assertEqual(resp.status_code, 403)

    def test_dosen_biasa_tidak_bisa_toggle_aktif(self):
        self.client.force_login(self.dosen)
        resp = self.client.post("/simda-dosen/tendik/1/toggle-aktif/")
        self.assertEqual(resp.status_code, 403)

    @patch("simda_dosen.views.DataTendik")
    def test_admin_bisa_akses_daftar(self, mock_cls):
        mock_qs = MagicMock()
        mock_cls.objects.using.return_value = mock_qs
        mock_qs.all.return_value = mock_qs
        mock_qs.order_by.return_value = []

        self.client.force_login(self.admin)
        resp = self.client.get("/simda-dosen/tendik/")

        self.assertEqual(resp.status_code, 200)
        mock_cls.objects.using.assert_called_with("simda")

    @patch("simda_dosen.views.DataTendik")
    def test_admin_bisa_cari(self, mock_cls):
        mock_qs = MagicMock()
        mock_cls.objects.using.return_value = mock_qs
        mock_qs.all.return_value = mock_qs
        mock_qs.filter.return_value = mock_qs
        mock_qs.order_by.return_value = []

        self.client.force_login(self.admin)
        resp = self.client.get("/simda-dosen/tendik/", {"q": "Meylan"})

        self.assertEqual(resp.status_code, 200)
        mock_qs.filter.assert_called_once()

    @patch("simda_dosen.forms.AgamaPublik")
    @patch("simda_dosen.forms.GolonganPublik")
    @patch("simda_dosen.forms.StatusKepegawaianPublik")
    @patch("simda_dosen.forms.JenisKepegawaianPublik")
    @patch("simda_dosen.forms.UnitKerja")
    def test_admin_bisa_buka_form_tambah(self, mock_unit, mock_jenis, mock_status, mock_golongan, mock_agama):
        for mock_ref in (mock_unit, mock_jenis, mock_status, mock_golongan, mock_agama):
            mock_ref.objects.using.return_value.filter.return_value.order_by.return_value = []
            mock_ref.objects.using.return_value.all.return_value = []
            mock_ref.objects.using.return_value.order_by.return_value = []

        self.client.force_login(self.admin)
        resp = self.client.get("/simda-dosen/tendik/tambah/")

        self.assertEqual(resp.status_code, 200)

    @patch("simda_dosen.views.DataTendik")
    def test_admin_bisa_toggle_aktif(self, mock_cls):
        # spec= WAJIB di sini -- get_object_or_404 pakai duck-typing
        # hasattr(klass, '_default_manager'); MagicMock() polos akan
        # auto-vivify atribut APA PUN jadi "ada" (hasattr selalu True),
        # bikin get_object_or_404 salah jalur ke klass._default_manager
        # .all().get(...) alih-alih queryset.get(...) yang di-mock.
        mock_qs = MagicMock(spec=["get", "filter", "all", "order_by"])
        mock_cls.objects.using.return_value = mock_qs
        mock_instance = MagicMock(is_active=True, nama_lengkap="Contoh Tendik")
        mock_qs.get.return_value = mock_instance

        self.client.force_login(self.admin)
        resp = self.client.post("/simda-dosen/tendik/1/toggle-aktif/")

        self.assertEqual(resp.status_code, 302)
        self.assertFalse(mock_instance.is_active)
        mock_instance.save.assert_called_once_with(update_fields=["is_active"])


class BisaTambahTridarmaTest(TestCase):
    """bisa_tambah_tridarma() -- gerbang TAMBAH (create) data Profil/Tri
    Dharma per 2026-08-03: menambahkan data ATAS NAMA dosen lain cuma
    boleh admin/operator (Dekan/Wadek/Kaprodi/Sekprodi/Rektorat/Biro
    TIDAK LAGI boleh, meski dapat_kelola() masih True untuk mereka --
    dipakai Edit/Hapus). Data diri sendiri selalu boleh siapa pun."""

    def setUp(self):
        self.dosen_ft = User.objects.create_user(
            username="bisatambah_dosen", password="testpass123", role="dosen", kode_fakultas="FT",
        )
        self.admin = User.objects.create_user(username="bisatambah_admin", password="testpass123", role="admin")
        self.operator_ft = User.objects.create_user(
            username="bisatambah_operator", password="testpass123", role="operator", kode_fakultas="FT",
        )
        self.dekan_ft = User.objects.create_user(
            username="bisatambah_dekan", password="testpass123", role="dekan", kode_fakultas="FT",
        )
        self.rektorat = User.objects.create_user(username="bisatambah_rektorat", password="testpass123", role="rektorat")

    def test_diri_sendiri_selalu_boleh(self):
        self.assertTrue(bisa_tambah_tridarma(self.dekan_ft, self.dekan_ft))
        self.assertTrue(bisa_tambah_tridarma(self.rektorat, self.rektorat))

    def test_admin_boleh_untuk_dosen_lain(self):
        self.assertTrue(bisa_tambah_tridarma(self.admin, self.dosen_ft))

    def test_operator_fakultas_sama_boleh_untuk_dosen_lain(self):
        self.assertTrue(bisa_tambah_tridarma(self.operator_ft, self.dosen_ft))

    def test_dekan_fakultas_sama_tidak_lagi_boleh_untuk_dosen_lain(self):
        self.assertFalse(bisa_tambah_tridarma(self.dekan_ft, self.dosen_ft))

    def test_rektorat_tidak_boleh_untuk_dosen_lain(self):
        self.assertFalse(bisa_tambah_tridarma(self.rektorat, self.dosen_ft))
