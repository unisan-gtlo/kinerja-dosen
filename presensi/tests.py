from unittest.mock import patch, MagicMock

from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APITestCase

from accounts.models import User
from .geo import dalam_radius, jarak_meter
from .models import LogKecurangan, LokasiKantor, Perangkat, Presensi
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
