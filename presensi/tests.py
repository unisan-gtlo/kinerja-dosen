from unittest.mock import patch, MagicMock

from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APITestCase

from accounts.models import User
from .geo import dalam_radius, jarak_meter
from .models import LogKecurangan, LokasiKantor, Perangkat, Presensi, StatusPresensi, TingkatRisiko
from .utils import get_dosen_by_nidn


class JarakMeterTest(TestCase):
    """Formula Haversine dipakai sebagai pengganti PostGIS/GDAL (lihat
    presensi/geo.py) -- pastikan hasilnya masuk akal untuk skala geofence."""

    def test_titik_sama_berjarak_nol(self):
        self.assertEqual(jarak_meter(-6.2, 106.8, -6.2, 106.8), 0)

    def test_satu_derajat_lintang_sekitar_111km(self):
        jarak = jarak_meter(0, 0, 1, 0)
        self.assertAlmostEqual(jarak, 111_320, delta=1_000)


class DalamRadiusTest(TestCase):
    """Kasus normal (dalam radius) dan kasus kecurangan/di luar radius."""

    def setUp(self):
        self.lokasi = LokasiKantor.objects.create(
            nama="Kampus Utama", latitude=0.0, longitude=0.0, radius_meter=100,
        )

    def test_titik_dalam_radius_diterima(self):
        # ~55 meter dari pusat (0.0005 derajat lintang)
        self.assertTrue(dalam_radius(0.0005, 0.0, self.lokasi))

    def test_titik_di_luar_radius_ditolak(self):
        # ~1.1 km dari pusat (0.01 derajat lintang) -- kasus "di_luar_radius"
        self.assertFalse(dalam_radius(0.01, 0.0, self.lokasi))


class PresensiUniqueTogetherTest(TestCase):
    """Satu dosen tidak boleh punya dua baris Presensi di tanggal yang sama."""

    def test_presensi_duplikat_nidn_tanggal_ditolak(self):
        Presensi.objects.create(nidn="1234567890", tanggal="2026-07-28")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Presensi.objects.create(nidn="1234567890", tanggal="2026-07-28")


class PerangkatUniqueTogetherTest(TestCase):
    """Satu device_id tidak boleh didaftarkan dua kali untuk dosen yang sama."""

    def test_perangkat_duplikat_ditolak(self):
        Perangkat.objects.create(nidn="1234567890", device_id="device-a")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Perangkat.objects.create(nidn="1234567890", device_id="device-a")


class GetDosenByNidnTest(TestCase):
    """Unit test murni (di-mock) karena DataDosen hidup di database SIMDA
    terpisah (alias koneksi 'simda') yang tidak selalu tersedia saat test."""

    def test_nidn_kosong_mengembalikan_none(self):
        self.assertIsNone(get_dosen_by_nidn(""))
        self.assertIsNone(get_dosen_by_nidn(None))

    @patch("presensi.utils.DataDosen")
    def test_query_dilakukan_lewat_koneksi_simda(self, mock_data_dosen):
        mock_qs = MagicMock()
        mock_data_dosen.objects.using.return_value = mock_qs
        mock_qs.filter.return_value = mock_qs

        get_dosen_by_nidn("1234567890")

        mock_data_dosen.objects.using.assert_called_once_with("simda")
        mock_qs.filter.assert_called_once_with(nidn="1234567890")
        mock_qs.first.assert_called_once()


def _buat_dosen_user(nidn="1234567890", username="dosen1"):
    return User.objects.create_user(
        username=username, password="testpass123", role="dosen", nidn=nidn,
    )


class AbsenMasukAPITest(APITestCase):
    """Endpoint POST /api/presensi/masuk -- kasus normal & kasus kecurangan."""

    def setUp(self):
        self.user = _buat_dosen_user()
        self.client.force_authenticate(user=self.user)
        self.lokasi = LokasiKantor.objects.create(
            nama="Kampus Utama", latitude=0.0, longitude=0.0, radius_meter=100,
        )
        self.payload_dalam_radius = {
            "lat": 0.0005, "lng": 0.0, "akurasi_m": 10, "device_id": "dev-1",
        }

    def test_dalam_radius_diterima_dan_tersimpan(self):
        resp = self.client.post("/api/presensi/masuk", self.payload_dalam_radius)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["diterima"])
        self.assertTrue(
            Presensi.objects.filter(nidn=self.user.nidn, waktu_masuk__isnull=False).exists()
        )

    def test_di_luar_radius_ditolak_dan_dicatat_kecurangan(self):
        resp = self.client.post("/api/presensi/masuk", {
            "lat": 0.01, "lng": 0.0, "akurasi_m": 10, "device_id": "dev-1",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["diterima"])
        self.assertEqual(resp.data["alasan"], "di_luar_radius")
        self.assertTrue(
            LogKecurangan.objects.filter(nidn=self.user.nidn, jenis_anomali="di_luar_radius").exists()
        )
        self.assertFalse(Presensi.objects.filter(nidn=self.user.nidn).exists())

    def test_akurasi_gps_buruk_ditolak(self):
        resp = self.client.post("/api/presensi/masuk", {
            "lat": 0.0, "lng": 0.0, "akurasi_m": 999, "device_id": "dev-1",
        })
        self.assertFalse(resp.data["diterima"])
        self.assertEqual(resp.data["alasan"], "akurasi_buruk")

    def test_absen_masuk_dobel_di_hari_sama_ditolak(self):
        self.client.post("/api/presensi/masuk", self.payload_dalam_radius)
        resp = self.client.post("/api/presensi/masuk", self.payload_dalam_radius)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["alasan"], "sudah_absen_masuk")

    def test_tanpa_autentikasi_ditolak(self):
        self.client.force_authenticate(user=None)
        resp = self.client.post("/api/presensi/masuk", self.payload_dalam_radius)
        self.assertEqual(resp.status_code, 401)


class AbsenPulangAPITest(APITestCase):
    """Endpoint POST /api/presensi/pulang."""

    def setUp(self):
        self.user = _buat_dosen_user()
        self.client.force_authenticate(user=self.user)
        LokasiKantor.objects.create(
            nama="Kampus Utama", latitude=0.0, longitude=0.0, radius_meter=100,
        )
        self.payload = {"lat": 0.0005, "lng": 0.0, "akurasi_m": 10, "device_id": "dev-1"}

    def test_pulang_tanpa_absen_masuk_ditolak(self):
        resp = self.client.post("/api/presensi/pulang", self.payload)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["alasan"], "belum_absen_masuk")

    def test_pulang_setelah_masuk_diterima(self):
        self.client.post("/api/presensi/masuk", self.payload)
        resp = self.client.post("/api/presensi/pulang", self.payload)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["diterima"])
        self.assertTrue(
            Presensi.objects.filter(nidn=self.user.nidn, waktu_pulang__isnull=False).exists()
        )


class HalamanAbsenViewTest(TestCase):
    """Halaman web /presensi/ -- harus login dulu, dan API di belakangnya
    bisa dipanggil lewat sesi Django (bukan cuma JWT)."""

    def test_tanpa_login_dialihkan_ke_halaman_login(self):
        resp = self.client.get("/presensi/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp.url)

    def test_sudah_login_bisa_akses_halaman(self):
        user = User.objects.create_user(username="dosen2", password="testpass123", role="dosen", nidn="1234567891")
        self.client.force_login(user)
        resp = self.client.get("/presensi/")
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "presensi/absen.html")

    def test_status_hari_ini_bisa_dipanggil_lewat_sesi_login(self):
        """API DRF harus menerima sesi Django (SessionAuthentication),
        bukan cuma token JWT -- dipakai oleh templates/presensi/absen.html."""
        user = User.objects.create_user(username="dosen3", password="testpass123", role="dosen", nidn="1234567892")
        self.client.force_login(user)
        resp = self.client.get("/api/presensi/status-hari-ini")
        self.assertEqual(resp.status_code, 200)


class TinjauPresensiViewTest(TestCase):
    """Halaman HR/admin untuk meninjau presensi ditandai -- kasus normal
    (setuju/tolak) & kasus akses (role tidak berwenang, scoping fakultas/prodi)."""

    def setUp(self):
        self.dosen_a = User.objects.create_user(
            username="dosenA", password="testpass123", role="dosen",
            nidn="1111111111", kode_prodi="TI", kode_fakultas="FT",
        )
        self.dosen_b = User.objects.create_user(
            username="dosenB", password="testpass123", role="dosen",
            nidn="2222222222", kode_prodi="SI", kode_fakultas="FT",
        )
        self.presensi_a = Presensi.objects.create(
            nidn=self.dosen_a.nidn, tanggal="2026-07-28", ditandai=True,
            tingkat_risiko=TingkatRisiko.SEDANG,
        )
        self.presensi_b = Presensi.objects.create(
            nidn=self.dosen_b.nidn, tanggal="2026-07-28", ditandai=True,
            tingkat_risiko=TingkatRisiko.SEDANG,
        )

    def test_dosen_biasa_tidak_bisa_akses(self):
        self.client.force_login(self.dosen_a)
        resp = self.client.get("/presensi/tinjau/")
        self.assertEqual(resp.status_code, 403)

    def test_admin_melihat_semua_presensi_ditandai(self):
        admin = User.objects.create_user(username="admin1", password="testpass123", role="admin")
        self.client.force_login(admin)
        resp = self.client.get("/presensi/tinjau/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.dosen_a.nidn)
        self.assertContains(resp, self.dosen_b.nidn)

    def test_kaprodi_hanya_melihat_prodi_sendiri(self):
        kaprodi = User.objects.create_user(
            username="kaprodiTI", password="testpass123", role="kaprodi", kode_prodi="TI",
        )
        self.client.force_login(kaprodi)
        resp = self.client.get("/presensi/tinjau/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.dosen_a.nidn)
        self.assertNotContains(resp, self.dosen_b.nidn)

    def test_setujui_presensi_menghapus_tanda(self):
        admin = User.objects.create_user(username="admin2", password="testpass123", role="admin")
        self.client.force_login(admin)
        resp = self.client.post(f"/presensi/tinjau/{self.presensi_a.id}/putuskan/", {"aksi": "setujui"})
        self.assertEqual(resp.status_code, 302)
        self.presensi_a.refresh_from_db()
        self.assertFalse(self.presensi_a.ditandai)
        self.assertEqual(self.presensi_a.tingkat_risiko, TingkatRisiko.RENDAH)

    def test_tolak_presensi_tercatat_di_log_kecurangan(self):
        admin = User.objects.create_user(username="admin3", password="testpass123", role="admin")
        self.client.force_login(admin)
        resp = self.client.post(f"/presensi/tinjau/{self.presensi_a.id}/putuskan/", {"aksi": "tolak"})
        self.assertEqual(resp.status_code, 302)
        self.presensi_a.refresh_from_db()
        self.assertFalse(self.presensi_a.ditandai)
        self.assertEqual(self.presensi_a.status, StatusPresensi.DITOLAK)
        self.assertTrue(
            LogKecurangan.objects.filter(nidn=self.dosen_a.nidn, jenis_anomali="ditolak_hr").exists()
        )

    def test_kaprodi_tidak_bisa_putuskan_presensi_di_luar_prodi(self):
        kaprodi = User.objects.create_user(
            username="kaprodiTI2", password="testpass123", role="kaprodi", kode_prodi="TI",
        )
        self.client.force_login(kaprodi)
        resp = self.client.post(f"/presensi/tinjau/{self.presensi_b.id}/putuskan/", {"aksi": "setujui"})
        self.assertEqual(resp.status_code, 403)
        self.presensi_b.refresh_from_db()
        self.assertTrue(self.presensi_b.ditandai)
