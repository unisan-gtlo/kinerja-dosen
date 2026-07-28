import io
from datetime import datetime as dt, time as dt_time
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import numpy as np
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from PIL import Image
from rest_framework.test import APITestCase

from accounts.models import User
from .decision import HasilCekWajah, verifikasi_wajah
from .face import dekripsi_embedding, ekstrak_satu_wajah, enkripsi_embedding, kemiripan_kosinus
from .geo import dalam_radius, jarak_meter
from .models import (
    EnrolmentWajah, LogKecurangan, LokasiKantor, Perangkat, Presensi, StatusPresensi, TingkatRisiko,
)
from .rekap import data_presensi_harian, ringkasan_hari_ini, top_telat_hari_ini, tren_mingguan
from .utils import get_dosen_by_nidn


def _foto_palsu(nama="selfie.jpg"):
    """Gambar JPEG kecil yang VALID (supaya lolos validasi ImageField DRF),
    tapi tidak ada wajah asli di dalamnya -- deteksi wajah selalu di-mock
    di test ini (model InsightFace berat, tidak perlu diunduh saat test)."""
    buf = io.BytesIO()
    Image.new("RGB", (100, 100), color=(120, 120, 120)).save(buf, format="JPEG")
    return SimpleUploadedFile(nama, buf.getvalue(), content_type="image/jpeg")


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


class KemiripanEnkripsiEmbeddingTest(TestCase):
    """Matematika murni (kemiripan kosinus) & roundtrip enkripsi Fernet --
    tidak butuh model InsightFace sama sekali."""

    def test_vektor_identik_kemiripan_satu(self):
        a = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        self.assertAlmostEqual(kemiripan_kosinus(a, a), 1.0, places=5)

    def test_vektor_ortogonal_kemiripan_nol(self):
        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([0.0, 1.0], dtype=np.float32)
        self.assertAlmostEqual(kemiripan_kosinus(a, b), 0.0, places=5)

    def test_roundtrip_enkripsi_dekripsi_embedding(self):
        embedding = np.random.rand(512).astype(np.float32)
        terenkripsi = enkripsi_embedding(embedding)
        hasil = dekripsi_embedding(terenkripsi)
        self.assertTrue(np.allclose(embedding, hasil))


class EkstrakSatuWajahTest(TestCase):
    """presensi.face.ekstrak_satu_wajah -- heuristik liveness sederhana
    (persis 1 wajah, skor deteksi cukup, ukuran wajah wajar). Model
    InsightFace di-mock lewat get_face_app."""

    def _wajah(self, det_score=0.9, bbox=(10, 10, 90, 90)):
        return SimpleNamespace(
            det_score=det_score, bbox=list(bbox),
            embedding=np.array([1.0, 0.0], dtype=np.float32),
        )

    @patch("presensi.face.get_face_app")
    def test_satu_wajah_jelas_lolos(self, mock_get_app):
        mock_get_app.return_value.get.return_value = [self._wajah()]
        wajah, alasan = ekstrak_satu_wajah(_foto_palsu())
        self.assertIsNotNone(wajah)
        self.assertIsNone(alasan)

    @patch("presensi.face.get_face_app")
    def test_tidak_ada_wajah_gagal(self, mock_get_app):
        mock_get_app.return_value.get.return_value = []
        wajah, alasan = ekstrak_satu_wajah(_foto_palsu())
        self.assertIsNone(wajah)
        self.assertEqual(alasan, "liveness_gagal")

    @patch("presensi.face.get_face_app")
    def test_lebih_dari_satu_wajah_gagal(self, mock_get_app):
        mock_get_app.return_value.get.return_value = [self._wajah(), self._wajah()]
        wajah, alasan = ekstrak_satu_wajah(_foto_palsu())
        self.assertIsNone(wajah)
        self.assertEqual(alasan, "liveness_gagal")

    @patch("presensi.face.get_face_app")
    def test_skor_deteksi_rendah_gagal(self, mock_get_app):
        mock_get_app.return_value.get.return_value = [self._wajah(det_score=0.1)]
        wajah, alasan = ekstrak_satu_wajah(_foto_palsu())
        self.assertIsNone(wajah)
        self.assertEqual(alasan, "liveness_gagal")

    @patch("presensi.face.get_face_app")
    def test_wajah_terlalu_kecil_gagal(self, mock_get_app):
        # foto 100x100, tinggi kotak wajah cuma 5px (rasio 0.05 < 0.15)
        mock_get_app.return_value.get.return_value = [self._wajah(bbox=(45, 45, 55, 50))]
        wajah, alasan = ekstrak_satu_wajah(_foto_palsu())
        self.assertIsNone(wajah)
        self.assertEqual(alasan, "liveness_gagal")


class VerifikasiWajahTest(TestCase):
    """presensi.decision.verifikasi_wajah -- syarat 2 lengkap (harus sudah
    enrolment DAN wajah cocok). ekstrak_satu_wajah di-mock."""

    def setUp(self):
        self.user = _buat_dosen_user()
        self.user_lain = _buat_dosen_user(nidn="9999999999", username="belum_enrolment")
        self.embedding_asli = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        EnrolmentWajah.objects.create(
            user=self.user,
            embedding_terenkripsi=enkripsi_embedding(self.embedding_asli),
            versi_model="tes", consent_disetujui=True, consent_pada=timezone.now(),
        )

    def test_belum_enrolment_gagal(self):
        hasil = verifikasi_wajah(self.user_lain, _foto_palsu())
        self.assertFalse(hasil.lolos)
        self.assertEqual(hasil.alasan, "belum_enrolment_wajah")

    @patch("presensi.decision.ekstrak_satu_wajah")
    def test_liveness_gagal_diteruskan(self, mock_ekstrak):
        mock_ekstrak.return_value = (None, "liveness_gagal")
        hasil = verifikasi_wajah(self.user, _foto_palsu())
        self.assertFalse(hasil.lolos)
        self.assertEqual(hasil.alasan, "liveness_gagal")

    @patch("presensi.decision.ekstrak_satu_wajah")
    def test_wajah_cocok_lolos(self, mock_ekstrak):
        mock_ekstrak.return_value = (SimpleNamespace(embedding=self.embedding_asli), None)
        hasil = verifikasi_wajah(self.user, _foto_palsu())
        self.assertTrue(hasil.lolos)
        self.assertGreater(hasil.skor_kemiripan, 0.9)

    @patch("presensi.decision.ekstrak_satu_wajah")
    def test_wajah_tidak_cocok_gagal(self, mock_ekstrak):
        embedding_beda = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        mock_ekstrak.return_value = (SimpleNamespace(embedding=embedding_beda), None)
        hasil = verifikasi_wajah(self.user, _foto_palsu())
        self.assertFalse(hasil.lolos)
        self.assertEqual(hasil.alasan, "wajah_tidak_cocok")


class PresensiUniqueTogetherTest(TestCase):
    """Satu orang tidak boleh punya dua baris Presensi di tanggal yang sama."""

    def test_presensi_duplikat_user_tanggal_ditolak(self):
        user = _buat_dosen_user()
        Presensi.objects.create(user=user, tanggal="2026-07-28")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Presensi.objects.create(user=user, tanggal="2026-07-28")


class PerangkatUniqueTogetherTest(TestCase):
    """Satu device_id tidak boleh didaftarkan dua kali untuk orang yang sama."""

    def test_perangkat_duplikat_ditolak(self):
        user = _buat_dosen_user()
        Perangkat.objects.create(user=user, device_id="device-a")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Perangkat.objects.create(user=user, device_id="device-a")


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


def _payload_absen(**override):
    """Payload multipart untuk /api/presensi/masuk|pulang -- selfie foto
    BARU tiap panggilan (bukan objek yang dipakai ulang), supaya aman
    dipakai berkali-kali dalam satu test (file upload cuma bisa dibaca
    sekali per request)."""
    data = {
        "lat": 0.0005, "lng": 0.0, "akurasi_m": 10, "device_id": "dev-1",
        "selfie": _foto_palsu(),
    }
    data.update(override)
    return data


class AbsenMasukAPITest(APITestCase):
    """Endpoint POST /api/presensi/masuk -- gerbang-DAN cek lokasi + wajah,
    kasus normal & kasus kecurangan. verifikasi_wajah di-mock supaya tidak
    perlu model InsightFace sungguhan (sudah diuji terpisah, lihat
    VerifikasiWajahTest & EkstrakSatuWajahTest)."""

    def setUp(self):
        self.user = _buat_dosen_user()
        self.client.force_authenticate(user=self.user)
        self.lokasi = LokasiKantor.objects.create(
            nama="Kampus Utama", latitude=0.0, longitude=0.0, radius_meter=100,
        )

    @patch("presensi.views.verifikasi_wajah")
    def test_dalam_radius_dan_wajah_cocok_diterima_rendah(self, mock_verifikasi):
        mock_verifikasi.return_value = HasilCekWajah(True, None, 0.95)
        resp = self.client.post("/api/presensi/masuk", _payload_absen(), format="multipart")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["diterima"])
        self.assertEqual(resp.data["tingkat_risiko"], TingkatRisiko.RENDAH)
        presensi = Presensi.objects.get(user=self.user)
        self.assertFalse(presensi.ditandai)
        self.assertEqual(presensi.tingkat_risiko, TingkatRisiko.RENDAH)

    def test_di_luar_radius_ditolak_dan_dicatat_kecurangan(self):
        # Gerbang berhenti di cek lokasi -- verifikasi_wajah tidak perlu di-mock.
        resp = self.client.post("/api/presensi/masuk", _payload_absen(lat=0.01), format="multipart")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["diterima"])
        self.assertEqual(resp.data["alasan"], "di_luar_radius")
        self.assertTrue(
            LogKecurangan.objects.filter(user=self.user, jenis_anomali="di_luar_radius").exists()
        )
        self.assertFalse(Presensi.objects.filter(user=self.user).exists())

    def test_akurasi_gps_buruk_ditolak(self):
        resp = self.client.post("/api/presensi/masuk", _payload_absen(akurasi_m=999), format="multipart")
        self.assertFalse(resp.data["diterima"])
        self.assertEqual(resp.data["alasan"], "akurasi_buruk")

    @patch("presensi.views.verifikasi_wajah")
    def test_wajah_tidak_cocok_ditolak_dan_dicatat_kecurangan(self, mock_verifikasi):
        mock_verifikasi.return_value = HasilCekWajah(False, "wajah_tidak_cocok", 0.1)
        resp = self.client.post("/api/presensi/masuk", _payload_absen(), format="multipart")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["diterima"])
        self.assertEqual(resp.data["alasan"], "wajah_tidak_cocok")
        self.assertTrue(
            LogKecurangan.objects.filter(user=self.user, jenis_anomali="wajah_tidak_cocok").exists()
        )
        self.assertFalse(Presensi.objects.filter(user=self.user).exists())

    @patch("presensi.views.verifikasi_wajah")
    def test_belum_enrolment_wajah_ditolak_tanpa_log_kecurangan(self, mock_verifikasi):
        # "Belum enrolment" itu soal kesiapan data, bukan indikasi curang --
        # jangan dicatat sebagai LogKecurangan (lihat SKOR_ANOMALI di views.py).
        mock_verifikasi.return_value = HasilCekWajah(False, "belum_enrolment_wajah", None)
        resp = self.client.post("/api/presensi/masuk", _payload_absen(), format="multipart")
        self.assertFalse(resp.data["diterima"])
        self.assertEqual(resp.data["alasan"], "belum_enrolment_wajah")
        self.assertFalse(
            LogKecurangan.objects.filter(user=self.user, jenis_anomali="belum_enrolment_wajah").exists()
        )

    @patch("presensi.views.verifikasi_wajah")
    def test_absen_masuk_dobel_di_hari_sama_ditolak(self, mock_verifikasi):
        mock_verifikasi.return_value = HasilCekWajah(True, None, 0.95)
        self.client.post("/api/presensi/masuk", _payload_absen(), format="multipart")
        resp = self.client.post("/api/presensi/masuk", _payload_absen(), format="multipart")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["alasan"], "sudah_absen_masuk")

    def test_tanpa_autentikasi_ditolak(self):
        self.client.force_authenticate(user=None)
        resp = self.client.post("/api/presensi/masuk", _payload_absen(), format="multipart")
        self.assertEqual(resp.status_code, 401)


class AbsenPulangAPITest(APITestCase):
    """Endpoint POST /api/presensi/pulang."""

    def setUp(self):
        self.user = _buat_dosen_user()
        self.client.force_authenticate(user=self.user)
        LokasiKantor.objects.create(
            nama="Kampus Utama", latitude=0.0, longitude=0.0, radius_meter=100,
        )

    def test_pulang_tanpa_absen_masuk_ditolak(self):
        resp = self.client.post("/api/presensi/pulang", _payload_absen(), format="multipart")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["alasan"], "belum_absen_masuk")

    @patch("presensi.views.verifikasi_wajah")
    def test_pulang_setelah_masuk_diterima(self, mock_verifikasi):
        mock_verifikasi.return_value = HasilCekWajah(True, None, 0.95)
        self.client.post("/api/presensi/masuk", _payload_absen(), format="multipart")
        resp = self.client.post("/api/presensi/pulang", _payload_absen(), format="multipart")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["diterima"])
        self.assertTrue(
            Presensi.objects.filter(user=self.user, waktu_pulang__isnull=False).exists()
        )


class EnrolmentWajahAPITest(APITestCase):
    """Endpoint POST /api/presensi/enrolment-wajah."""

    def setUp(self):
        self.user = _buat_dosen_user()
        self.client.force_authenticate(user=self.user)

    @patch("presensi.views.ekstrak_satu_wajah")
    def test_enrolment_berhasil(self, mock_ekstrak):
        mock_ekstrak.return_value = (SimpleNamespace(embedding=np.array([1.0, 0.0], dtype=np.float32)), None)
        resp = self.client.post(
            "/api/presensi/enrolment-wajah",
            {"foto": [_foto_palsu("a.jpg"), _foto_palsu("b.jpg")], "consent": True},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["status"], "ok")
        self.assertTrue(
            EnrolmentWajah.objects.filter(user=self.user, consent_disetujui=True).exists()
        )

    @patch("presensi.views.ekstrak_satu_wajah")
    def test_enrolment_gagal_kalau_wajah_tidak_konsisten_terdeteksi(self, mock_ekstrak):
        mock_ekstrak.return_value = (None, "liveness_gagal")
        resp = self.client.post(
            "/api/presensi/enrolment-wajah",
            {"foto": [_foto_palsu("a.jpg"), _foto_palsu("b.jpg")], "consent": True},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["alasan"], "wajah_tidak_terdeteksi_konsisten")

    def test_enrolment_tanpa_consent_ditolak(self):
        resp = self.client.post(
            "/api/presensi/enrolment-wajah",
            {"foto": [_foto_palsu("a.jpg"), _foto_palsu("b.jpg")], "consent": False},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 400)

    def test_enrolment_kurang_dari_dua_foto_ditolak(self):
        resp = self.client.post(
            "/api/presensi/enrolment-wajah",
            {"foto": [_foto_palsu("a.jpg")], "consent": True},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 400)


class HalamanAbsenViewTest(TestCase):
    """Halaman web /presensi/ -- harus login dulu, dan API di belakangnya
    bisa dipanggil lewat sesi Django (bukan cuma JWT)."""

    def test_tanpa_login_dialihkan_ke_halaman_login(self):
        resp = self.client.get("/presensi/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp.url)

    def test_sudah_login_bisa_akses_halaman(self):
        user = User.objects.create_user(
            username="dosen2", password="testpass123", role="dosen", nidn="1234567891",
            first_name="Budi", last_name="Santoso",
        )
        self.client.force_login(user)
        resp = self.client.get("/presensi/")
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "presensi/absen.html")
        self.assertEqual(resp.context["nama_tampil"], "Budi Santoso")
        self.assertEqual(resp.context["inisial"], "BS")
        self.assertIn(resp.context["sapaan"], ["Selamat pagi", "Selamat siang", "Selamat sore", "Selamat malam"])

    def test_status_hari_ini_bisa_dipanggil_lewat_sesi_login(self):
        """API DRF harus menerima sesi Django (SessionAuthentication),
        bukan cuma token JWT -- dipakai oleh templates/presensi/absen.html."""
        user = User.objects.create_user(username="dosen3", password="testpass123", role="dosen", nidn="1234567892")
        self.client.force_login(user)
        resp = self.client.get("/api/presensi/status-hari-ini")
        self.assertEqual(resp.status_code, 200)


class ServiceWorkerPresensiTest(TestCase):
    """Service worker PWA disajikan di /presensi/sw.js (BUKAN lewat
    WhiteNoise/static) supaya cakupannya otomatis /presensi/* tanpa perlu
    header Service-Worker-Allowed tambahan di Nginx."""

    def test_sw_bisa_diakses_tanpa_login(self):
        # Browser bisa saja minta sw.js sebelum sesi login "matang" --
        # jangan sampai ke-redirect ke halaman login.
        resp = self.client.get("/presensi/sw.js")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/javascript")


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
            user=self.dosen_a, tanggal="2026-07-28", ditandai=True,
            tingkat_risiko=TingkatRisiko.SEDANG,
        )
        self.presensi_b = Presensi.objects.create(
            user=self.dosen_b, tanggal="2026-07-28", ditandai=True,
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
            LogKecurangan.objects.filter(user=self.dosen_a, jenis_anomali="ditolak_hr").exists()
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


class RekapPresensiTest(TestCase):
    """Logika presensi/rekap.py -- dipakai dashboard admin & ekspor data.
    Skema presensi sudah generik (kunci user), fungsi-fungsi ini menerima
    daftar user_id -- cakupan dosen-only saat ini datang dari
    get_dosen_queryset di views.py, bukan dari rekap.py sendiri."""

    def setUp(self):
        self.dosen_a = User.objects.create_user(
            username="rekapA", password="testpass123", role="dosen",
            nidn="3333333333", kode_fakultas="FT", kode_prodi="TI",
        )
        self.dosen_b = User.objects.create_user(
            username="rekapB", password="testpass123", role="dosen",
            nidn="4444444444", kode_fakultas="FT", kode_prodi="TI",
        )
        self.lokasi = LokasiKantor.objects.create(
            nama="Kampus Utama", latitude=0.0, longitude=0.0, radius_meter=100,
            jam_masuk=dt_time(8, 0), toleransi_menit=15,
        )
        self.user_ids = [self.dosen_a.id, self.dosen_b.id]
        self.hari_ini = timezone.localdate()

    def test_ringkasan_menghitung_hadir_telat_belum_absen(self):
        Presensi.objects.create(
            user=self.dosen_a, tanggal=self.hari_ini, status=StatusPresensi.HADIR,
            waktu_masuk=timezone.now(),
        )
        Presensi.objects.create(
            user=self.dosen_b, tanggal=self.hari_ini, status=StatusPresensi.TELAT,
            waktu_masuk=timezone.now(),
        )
        ringkasan = ringkasan_hari_ini(self.user_ids, tanggal=self.hari_ini)
        self.assertEqual(ringkasan["total"], 2)
        self.assertEqual(ringkasan["hadir"], 1)
        self.assertEqual(ringkasan["telat"], 1)
        self.assertEqual(ringkasan["belum_absen"], 0)

    def test_ringkasan_belum_absen_kalau_tidak_ada_presensi(self):
        ringkasan = ringkasan_hari_ini(self.user_ids, tanggal=self.hari_ini)
        self.assertEqual(ringkasan["belum_absen"], 2)

    def test_tren_mingguan_hitung_per_hari(self):
        Presensi.objects.create(
            user=self.dosen_a, tanggal=self.hari_ini, status=StatusPresensi.HADIR,
            waktu_masuk=timezone.now(),
        )
        tren = tren_mingguan(self.user_ids, jumlah_hari=3, tanggal_akhir=self.hari_ini)
        self.assertEqual(len(tren), 3)
        self.assertEqual(tren[-1]["tanggal"], self.hari_ini)
        self.assertEqual(tren[-1]["jumlah"], 1)

    def test_top_telat_urut_dari_paling_telat(self):
        waktu_a = timezone.make_aware(dt.combine(self.hari_ini, dt_time(8, 10)))
        waktu_b = timezone.make_aware(dt.combine(self.hari_ini, dt_time(8, 40)))
        Presensi.objects.create(
            user=self.dosen_a, tanggal=self.hari_ini, status=StatusPresensi.TELAT,
            waktu_masuk=waktu_a, lokasi=self.lokasi,
        )
        Presensi.objects.create(
            user=self.dosen_b, tanggal=self.hari_ini, status=StatusPresensi.TELAT,
            waktu_masuk=waktu_b, lokasi=self.lokasi,
        )
        top = top_telat_hari_ini(self.user_ids, tanggal=self.hari_ini)
        self.assertEqual(len(top), 2)
        self.assertEqual(top[0]["presensi"].user_id, self.dosen_b.id)  # paling telat duluan
        self.assertGreater(top[0]["menit_telat"], top[1]["menit_telat"])

    def test_data_presensi_harian_sertakan_yang_belum_absen(self):
        Presensi.objects.create(
            user=self.dosen_a, tanggal=self.hari_ini, status=StatusPresensi.HADIR,
            waktu_masuk=timezone.now(),
        )
        dosen_qs = User.objects.filter(id__in=self.user_ids)
        daftar = data_presensi_harian(dosen_qs, self.hari_ini)
        self.assertEqual(len(daftar), 2)
        by_id = {d["dosen"].id: d["presensi"] for d in daftar}
        self.assertIsNotNone(by_id[self.dosen_a.id])
        self.assertIsNone(by_id[self.dosen_b.id])


class DashboardDataPresensiViewTest(TestCase):
    """Halaman /presensi/dashboard/, /presensi/data/, dan ekspor Excel --
    akses dibatasi sama seperti /presensi/tinjau/."""

    def setUp(self):
        self.dosen = User.objects.create_user(
            username="dashdosen", password="testpass123", role="dosen",
            nidn="5555555555", kode_fakultas="FT", kode_prodi="TI",
        )

    def test_dosen_biasa_tidak_bisa_akses_dashboard(self):
        self.client.force_login(self.dosen)
        resp = self.client.get("/presensi/dashboard/")
        self.assertEqual(resp.status_code, 403)

    def test_admin_bisa_akses_dashboard(self):
        admin = User.objects.create_user(username="dashadmin", password="testpass123", role="admin")
        self.client.force_login(admin)
        resp = self.client.get("/presensi/dashboard/")
        self.assertEqual(resp.status_code, 200)

    def test_admin_bisa_akses_data_presensi(self):
        admin = User.objects.create_user(username="dataadmin", password="testpass123", role="admin")
        self.client.force_login(admin)
        resp = self.client.get("/presensi/data/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.dosen.nidn)

    def test_dosen_biasa_tidak_bisa_ekspor(self):
        self.client.force_login(self.dosen)
        resp = self.client.get("/presensi/data/ekspor/")
        self.assertEqual(resp.status_code, 403)

    def test_admin_bisa_ekspor_excel(self):
        admin = User.objects.create_user(username="ekspoladmin", password="testpass123", role="admin")
        self.client.force_login(admin)
        resp = self.client.get("/presensi/data/ekspor/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
