from unittest.mock import Mock, patch

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from presensi.models import IzinCuti


class DashboardTendikTest(TestCase):
    """Dashboard role=tendik -- sengaja BUKAN Tri Dharma (Penelitian/
    Pengabdian/dst), fokus ringkasan presensi diri sendiri (lihat
    dashboard/views.py, CLAUDE.md bagian Dashboard Tendik). User test
    SENGAJA tidak diisi nip_yayasan supaya get_simda_tendik_or_none tidak
    perlu query SIMDA sungguhan (return None lebih awal) -- konsisten
    dengan get_simda_dosen_or_none yang juga tanpa proteksi DatabaseError
    di level ini (parity yang sudah ada, bukan celah baru)."""

    def setUp(self):
        self.tendik = User.objects.create_user(
            username="dashboardtendik", password="testpass123", role="tendik",
        )

    def test_tendik_bisa_akses_dashboard(self):
        self.client.force_login(self.tendik)
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("rekap_bulan_ini", resp.context)
        self.assertIn("tendik_profil", resp.context)
        self.assertIsNone(resp.context["tendik_profil"])

    def test_tanpa_tendik_profil_tampil_placeholder_avatar(self):
        # tendik_profil None (belum tertaut SIMDA) -- avatar jatuh ke
        # ikon placeholder, bukan <img> kosong/error.
        self.client.force_login(self.tendik)
        resp = self.client.get("/")
        self.assertContains(resp, "avatar-placeholder-tendik")

    @patch("dashboard.views.get_simda_tendik_or_none")
    def test_tendik_dengan_foto_tampil_avatar(self, mock_get):
        # Foto profil di dashboard tendik -- meniru pola avatar Profil
        # Saya di dashboard dosen (.avatar/.avatar-placeholder). Mock
        # BIASA (bukan MagicMock) -- MagicMock auto-implementasi
        # __getitem__ di level class, bikin resolusi variabel Django
        # ({{ tendik_profil.foto }}) salah ambil dictionary-lookup
        # duluan dan tidak pernah sampai ke attribute yang di-set manual
        # (lihat catatan sama di simda_dosen/tests.py::
        # test_avatar_foto_tampil_di_daftar).
        tendik_profil = Mock(nama_lengkap="Contoh Tendik", jabatan="Staf", unit_kerja_nama="LP3M")
        tendik_profil.foto.url = "/media/tendik/foto/contoh.jpg"
        mock_get.return_value = tendik_profil

        self.client.force_login(self.tendik)
        resp = self.client.get("/")

        self.assertContains(resp, '<img src="/media/tendik/foto/contoh.jpg" class="avatar-tendik"')

    def test_tendik_tidak_lihat_data_tri_dharma(self):
        # Dashboard tendik sengaja tidak set context Tri Dharma sama
        # sekali -- beda dari dashboard dosen maupun dashboard oversight
        # admin/dekan/dst yang keduanya penuh angka Penelitian/Pengabdian.
        self.client.force_login(self.tendik)
        resp = self.client.get("/")
        self.assertNotIn("total_penelitian", resp.context)

    def test_izin_menunggu_dihitung(self):
        hari_ini = timezone.localdate()
        IzinCuti.objects.create(
            user=self.tendik, tipe=IzinCuti.Tipe.IZIN,
            tanggal_mulai=hari_ini, tanggal_selesai=hari_ini, alasan="Contoh",
        )
        self.client.force_login(self.tendik)
        resp = self.client.get("/")
        self.assertEqual(resp.context["izin_menunggu"], 1)

    def test_tendik_tidak_lihat_menu_manajemen(self):
        # Regresi: section "Manajemen" (Rekap Data/Export Laporan) di
        # base.html dulu di-gate `role != 'dosen'` (negatif) -- bocor ke
        # tendik walau kedua link itu 100% berbasis data dosen. Sekarang
        # allowlist eksplisit mengecualikan tendik juga.
        self.client.force_login(self.tendik)
        resp = self.client.get("/")
        self.assertNotContains(resp, "Rekap Data")
