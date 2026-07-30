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
from .decision import (
    HasilCekWajah, hitung_ketepatan_masuk, hitung_ketepatan_pulang, resolve_kelompok, tentukan_status_waktu,
    verifikasi_wajah,
)
from .face import dekripsi_embedding, ekstrak_satu_wajah, enkripsi_embedding, kemiripan_kosinus
from .geo import dalam_radius, jarak_meter
from .models import (
    BATAS_MENIT_LEMBUR_WAJIB_KETERANGAN, EnrolmentWajah, HariLibur, IzinCuti, KelompokPresensi, LogKecurangan,
    LokasiKantor, ParafDosen, Perangkat, Presensi, StatusApprovalLembur, StatusPresensi, TargetKerjaBulanan,
    TingkatRisiko, format_jam_menit,
)
from .rekap import data_presensi_harian, rekap_bulanan_user, ringkasan_hari_ini, top_telat_hari_ini, tren_mingguan
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


class SeedKelompokPresensiTest(TestCase):
    """Data awal KelompokPresensi dibuat lewat migrasi -- lihat
    presensi/migrations/0006_seed_kelompok_presensi.py."""

    def test_kelompok_dosen_sesuai_spesifikasi(self):
        dosen = KelompokPresensi.objects.get(nama="Dosen")
        self.assertEqual(dosen.roles, ["dosen"])
        self.assertEqual(dosen.jam_masuk, dt_time(8, 0))
        self.assertEqual(dosen.jam_pulang, dt_time(14, 0))
        self.assertTrue(dosen.aktif)

    def test_kelompok_pejabat_sesuai_spesifikasi(self):
        pejabat = KelompokPresensi.objects.get(nama="Pejabat")
        self.assertIn("dekan", pejabat.roles)
        self.assertEqual(pejabat.jam_masuk, dt_time(8, 0))
        self.assertEqual(pejabat.jam_pulang, dt_time(16, 0))
        self.assertTrue(pejabat.aktif)


class ResolveKelompokTest(TestCase):
    """resolve_kelompok memetakan role akun ke KelompokPresensi otomatis --
    dipakai untuk snapshot Presensi.kelompok (lihat CLAUDE.md § 9)."""

    def setUp(self):
        # Data awal migrasi ("Dosen"/"Pejabat") dihapus dulu supaya test ini
        # terisolasi dari kelompok yang dibuat manual di sini.
        KelompokPresensi.objects.all().delete()
        self.kelompok_dosen = KelompokPresensi.objects.create(
            nama="Dosen Test", roles=["dosen"], jam_masuk=dt_time(8, 0), jam_pulang=dt_time(14, 0),
        )

    def test_role_dosen_meresolve_ke_kelompok_dosen(self):
        user = _buat_dosen_user()
        self.assertEqual(resolve_kelompok(user), self.kelompok_dosen)

    def test_role_tanpa_pemetaan_mengembalikan_none(self):
        user = User.objects.create_user(username="staf1", password="testpass123", role="admin")
        self.assertIsNone(resolve_kelompok(user))

    def test_kelompok_tidak_aktif_diabaikan(self):
        self.kelompok_dosen.aktif = False
        self.kelompok_dosen.save()
        user = _buat_dosen_user()
        self.assertIsNone(resolve_kelompok(user))


class TentukanStatusWaktuTest(TestCase):
    """Prioritas jam kerja KelompokPresensi > LokasiKantor, plus pengecualian
    hari libur & hari non-kerja kelompok -- lihat CLAUDE.md § 9."""

    def setUp(self):
        self.lokasi = LokasiKantor.objects.create(
            nama="Kampus Utama", latitude=0.0, longitude=0.0,
            jam_masuk=dt_time(8, 0), toleransi_menit=15,
        )
        self.kelompok_dosen = KelompokPresensi.objects.create(
            nama="Dosen Test", roles=["dosen"], hari_kerja=[0, 1, 2, 3, 4, 5],
            jam_masuk=dt_time(8, 0), jam_pulang=dt_time(14, 0), toleransi_menit=15,
        )

    def test_tepat_waktu_sesuai_jam_kelompok(self):
        status = tentukan_status_waktu(self.lokasi, dt_time(8, 10), kelompok=self.kelompok_dosen)
        self.assertEqual(status, StatusPresensi.HADIR)

    def test_telat_lewat_toleransi_kelompok(self):
        status = tentukan_status_waktu(self.lokasi, dt_time(8, 30), kelompok=self.kelompok_dosen)
        self.assertEqual(status, StatusPresensi.TELAT)

    def test_kelompok_diprioritaskan_di_atas_lokasi(self):
        # Lokasi jam_masuk 08.00, tapi kelompok jam_masuk 10.00 -- kelompok
        # yang harus dipakai, bukan lokasi.
        kelompok_siang = KelompokPresensi.objects.create(
            nama="Siang", roles=["operator"], jam_masuk=dt_time(10, 0), toleransi_menit=15,
        )
        status = tentukan_status_waktu(self.lokasi, dt_time(8, 30), kelompok=kelompok_siang)
        self.assertEqual(status, StatusPresensi.HADIR)

    def test_fallback_ke_lokasi_kalau_kelompok_none(self):
        # Role belum dipetakan ke kelompok mana pun -- pakai jam_masuk/
        # toleransi_menit LokasiKantor seperti sebelum fitur ini ada.
        status = tentukan_status_waktu(self.lokasi, dt_time(8, 30), kelompok=None)
        self.assertEqual(status, StatusPresensi.TELAT)

    def test_hari_libur_selalu_hadir_meski_lewat_jam(self):
        HariLibur.objects.create(tanggal="2026-08-17", keterangan="Hari libur uji", jenis="nasional")
        status = tentukan_status_waktu(
            self.lokasi, dt_time(23, 0), kelompok=self.kelompok_dosen,
            tanggal=dt.strptime("2026-08-17", "%Y-%m-%d").date(),
        )
        self.assertEqual(status, StatusPresensi.HADIR)

    def test_hari_non_kerja_kelompok_selalu_hadir(self):
        # 2026-08-16 adalah Minggu (weekday=6), tidak termasuk hari_kerja
        # kelompok Dosen (Senin-Sabtu, 0-5).
        tanggal_minggu = dt.strptime("2026-08-16", "%Y-%m-%d").date()
        self.assertEqual(tanggal_minggu.weekday(), 6)
        status = tentukan_status_waktu(
            self.lokasi, dt_time(23, 0), kelompok=self.kelompok_dosen, tanggal=tanggal_minggu,
        )
        self.assertEqual(status, StatusPresensi.HADIR)


class FormatJamMenitTest(TestCase):
    """format_jam_menit -- format durasi menit jadi "JJ:MM" untuk tampilan
    Riwayat & laporan bulanan (lihat CLAUDE.md § 9)."""

    def test_format_normal(self):
        self.assertEqual(format_jam_menit(465), "07:45")

    def test_format_nol(self):
        self.assertEqual(format_jam_menit(0), "00:00")

    def test_format_negatif_dianggap_nol(self):
        self.assertEqual(format_jam_menit(-30), "00:00")

    def test_format_none_dianggap_nol(self):
        self.assertEqual(format_jam_menit(None), "00:00")


class HitungKetepatanMasukPulangTest(TestCase):
    """hitung_ketepatan_masuk/pulang -- selisih murni dari jam kelompok/
    lokasi (TIDAK memperhitungkan toleransi_menit, beda dengan status
    HADIR/TELAT di tentukan_status_waktu)."""

    def setUp(self):
        self.lokasi = LokasiKantor.objects.create(
            nama="Kampus Utama", latitude=0.0, longitude=0.0, jam_masuk=dt_time(8, 0), jam_pulang=dt_time(16, 0),
        )
        self.kelompok = KelompokPresensi.objects.create(
            nama="Dosen Test", roles=["dosen"], hari_kerja=[0, 1, 2, 3, 4, 5],
            jam_masuk=dt_time(8, 0), jam_pulang=dt_time(14, 0), toleransi_menit=15,
        )

    def test_masuk_lebih_awal(self):
        awal, telat = hitung_ketepatan_masuk(self.lokasi, dt_time(7, 45), kelompok=self.kelompok)
        self.assertEqual((awal, telat), (15, 0))

    def test_masuk_terlambat(self):
        # Beda dengan status TELAT (yang menghitung toleransi), di sini
        # selisih MENTAH dari jam_masuk -- 10 menit tetap terhitung telat
        # walau masih dalam toleransi 15 menit status HADIR/TELAT.
        awal, telat = hitung_ketepatan_masuk(self.lokasi, dt_time(8, 10), kelompok=self.kelompok)
        self.assertEqual((awal, telat), (0, 10))

    def test_masuk_tepat_waktu(self):
        awal, telat = hitung_ketepatan_masuk(self.lokasi, dt_time(8, 0), kelompok=self.kelompok)
        self.assertEqual((awal, telat), (0, 0))

    def test_pulang_lebih_cepat(self):
        cepat, lembur = hitung_ketepatan_pulang(self.lokasi, dt_time(13, 30), kelompok=self.kelompok)
        self.assertEqual((cepat, lembur), (30, 0))

    def test_pulang_lembur(self):
        cepat, lembur = hitung_ketepatan_pulang(self.lokasi, dt_time(16, 30), kelompok=self.kelompok)
        self.assertEqual((cepat, lembur), (0, 150))

    def test_fallback_ke_lokasi_kalau_kelompok_none(self):
        awal, telat = hitung_ketepatan_masuk(self.lokasi, dt_time(8, 10), kelompok=None)
        self.assertEqual((awal, telat), (0, 10))

    def test_hari_libur_selalu_nol(self):
        HariLibur.objects.create(tanggal="2026-08-17", keterangan="Hari libur uji", jenis="nasional")
        tanggal = dt.strptime("2026-08-17", "%Y-%m-%d").date()
        awal, telat = hitung_ketepatan_masuk(self.lokasi, dt_time(23, 0), kelompok=self.kelompok, tanggal=tanggal)
        self.assertEqual((awal, telat), (0, 0))


class DurasiKerjaPresensiTest(TestCase):
    """Presensi.durasi_kerja_menit -- durasi kerja efektif, dibatasi ke jam
    pulang normal kalau lembur menunggu/ditolak (lihat CLAUDE.md § 9)."""

    def setUp(self):
        self.user = _buat_dosen_user()
        self.kelompok = KelompokPresensi.objects.create(
            nama="Dosen Test", roles=["dosen"], jam_masuk=dt_time(8, 0), jam_pulang=dt_time(14, 0),
        )
        self.tanggal = timezone.localdate()

    def _presensi(self, jam_masuk, jam_pulang, **override):
        defaults = dict(
            user=self.user, tanggal=self.tanggal, kelompok=self.kelompok,
            waktu_masuk=timezone.make_aware(dt.combine(self.tanggal, jam_masuk)),
            waktu_pulang=timezone.make_aware(dt.combine(self.tanggal, jam_pulang)),
        )
        defaults.update(override)
        return Presensi(**defaults)

    def test_durasi_normal_tanpa_lembur(self):
        presensi = self._presensi(dt_time(8, 0), dt_time(14, 0))
        self.assertEqual(presensi.durasi_kerja_menit, 360)
        self.assertEqual(presensi.durasi_kerja, "06:00")

    def test_durasi_lembur_disetujui_dihitung_penuh(self):
        presensi = self._presensi(
            dt_time(8, 0), dt_time(17, 0),
            menit_lembur=180, status_lembur=StatusApprovalLembur.DISETUJUI,
        )
        self.assertEqual(presensi.durasi_kerja_menit, 540)

    def test_durasi_lembur_menunggu_dibatasi_jam_normal(self):
        presensi = self._presensi(
            dt_time(8, 0), dt_time(17, 0),
            menit_lembur=180, status_lembur=StatusApprovalLembur.MENUNGGU,
        )
        self.assertEqual(presensi.durasi_kerja_menit, 360)  # dibatasi ke 14:00, bukan 17:00

    def test_durasi_lembur_ditolak_dibatasi_jam_normal(self):
        presensi = self._presensi(
            dt_time(8, 0), dt_time(17, 0),
            menit_lembur=180, status_lembur=StatusApprovalLembur.DITOLAK,
        )
        self.assertEqual(presensi.durasi_kerja_menit, 360)

    def test_belum_absen_pulang_durasi_nol(self):
        presensi = self._presensi(dt_time(8, 0), dt_time(14, 0))
        presensi.waktu_pulang = None
        self.assertEqual(presensi.durasi_kerja_menit, 0)


class SeedKelompokStafTendikTest(TestCase):
    """Data awal kelompok "Staf/Tendik" -- lihat presensi/migrations/
    0008_seed_kelompok_staf_tendik.py."""

    def test_kelompok_staf_tendik_sesuai_spesifikasi(self):
        staf = KelompokPresensi.objects.get(nama="Staf/Tendik")
        self.assertEqual(staf.roles, ["tendik"])
        self.assertEqual(staf.jam_masuk, dt_time(8, 0))
        self.assertEqual(staf.jam_pulang, dt_time(16, 0))
        self.assertTrue(staf.aktif)


class RekapBulananUserTest(TestCase):
    """rekap_bulanan_user -- total jam kerja sebulan vs TargetKerjaBulanan
    kelompoknya (lihat CLAUDE.md § 9)."""

    def setUp(self):
        self.user = _buat_dosen_user()
        self.kelompok = KelompokPresensi.objects.create(
            nama="Dosen Test", roles=["dosen"], jam_masuk=dt_time(8, 0), jam_pulang=dt_time(14, 0),
        )
        self.hari_ini = timezone.localdate()

    def test_total_menit_dijumlahkan_dari_semua_hari(self):
        # day=1 & day=2 selalu ada di bulan apa pun -- aman dari masalah
        # batas bulan tanpa perlu tahu tanggal hari ini persisnya.
        for hari in (1, 2):
            tanggal = self.hari_ini.replace(day=hari)
            Presensi.objects.create(
                user=self.user, tanggal=tanggal, kelompok=self.kelompok,
                waktu_masuk=timezone.make_aware(dt.combine(tanggal, dt_time(8, 0))),
                waktu_pulang=timezone.make_aware(dt.combine(tanggal, dt_time(14, 0))),
            )
        rekap = rekap_bulanan_user(self.user, self.hari_ini.month, self.hari_ini.year)
        self.assertEqual(rekap["total_menit"], 720)
        self.assertEqual(rekap["total_jam_kerja"], "12:00")
        self.assertEqual(rekap["kelompok"], self.kelompok)

    def test_presensi_ditolak_dikecualikan(self):
        Presensi.objects.create(
            user=self.user, tanggal=self.hari_ini, kelompok=self.kelompok, status=StatusPresensi.DITOLAK,
            waktu_masuk=timezone.make_aware(dt.combine(self.hari_ini, dt_time(8, 0))),
            waktu_pulang=timezone.make_aware(dt.combine(self.hari_ini, dt_time(14, 0))),
        )
        rekap = rekap_bulanan_user(self.user, self.hari_ini.month, self.hari_ini.year)
        self.assertEqual(rekap["total_menit"], 0)

    def test_target_diambil_dari_kelompok_dan_bulan_yang_cocok(self):
        Presensi.objects.create(
            user=self.user, tanggal=self.hari_ini, kelompok=self.kelompok,
            waktu_masuk=timezone.make_aware(dt.combine(self.hari_ini, dt_time(8, 0))),
            waktu_pulang=timezone.make_aware(dt.combine(self.hari_ini, dt_time(14, 0))),
        )
        TargetKerjaBulanan.objects.create(
            kelompok=self.kelompok, bulan=self.hari_ini.month, tahun=self.hari_ini.year,
            target_hari_kerja=24, target_jam_kerja=144,
        )
        rekap = rekap_bulanan_user(self.user, self.hari_ini.month, self.hari_ini.year)
        self.assertIsNotNone(rekap["target"])
        self.assertEqual(rekap["target"].target_hari_kerja, 24)

    def test_tidak_ada_presensi_target_kosong(self):
        rekap = rekap_bulanan_user(self.user, self.hari_ini.month, self.hari_ini.year)
        self.assertIsNone(rekap["target"])
        self.assertEqual(rekap["total_menit"], 0)


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

    @patch("presensi.views.verifikasi_wajah")
    def test_kelompok_disematkan_sebagai_snapshot(self, mock_verifikasi):
        # "Dosen" sudah ada dari data awal migrasi (lihat 0006_seed_kelompok_
        # presensi.py) -- role user default "dosen" harus otomatis meresolve
        # ke kelompok itu tanpa perlu setup tambahan di sini.
        mock_verifikasi.return_value = HasilCekWajah(True, None, 0.95)
        resp = self.client.post("/api/presensi/masuk", _payload_absen(), format="multipart")
        self.assertTrue(resp.data["diterima"])
        presensi = Presensi.objects.get(user=self.user)
        self.assertIsNotNone(presensi.kelompok)
        self.assertEqual(presensi.kelompok.nama, "Dosen")


class AbsenPulangAPITest(APITestCase):
    """Endpoint POST /api/presensi/pulang."""

    def setUp(self):
        self.user = _buat_dosen_user()
        self.client.force_authenticate(user=self.user)
        LokasiKantor.objects.create(
            nama="Kampus Utama", latitude=0.0, longitude=0.0, radius_meter=100,
        )
        # Dihitung SEBELUM test body (yang mem-patch timezone.now di beberapa
        # test) -- timezone.localdate() sendiri memanggil now() internal,
        # jadi kalau dipanggil di dalam test yang sudah di-patch, hasilnya
        # ikut jadi MagicMock, bukan tanggal asli.
        self.hari_ini = timezone.localdate()

    def test_pulang_tanpa_absen_masuk_ditolak(self):
        resp = self.client.post("/api/presensi/pulang", _payload_absen(), format="multipart")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["alasan"], "belum_absen_masuk")

    @patch("presensi.views.verifikasi_wajah")
    @patch("presensi.views.timezone.now")
    def test_pulang_setelah_masuk_diterima(self, mock_now, mock_verifikasi):
        # Waktu di-pin ke jam kerja normal (bukan real clock) -- tanpa ini,
        # test bisa gagal secara acak tergantung jam sungguhan server: kalau
        # kebetulan dijalankan >2 jam lewat jam pulang kelompok "Dosen"
        # (14.00), endpoint akan menolak karena keterangan_lembur wajib
        # (lihat AbsenPulangView), padahal test ini bukan soal lembur.
        mock_verifikasi.return_value = HasilCekWajah(True, None, 0.95)
        mock_now.return_value = timezone.make_aware(dt.combine(self.hari_ini, dt_time(8, 0)))
        self.client.post("/api/presensi/masuk", _payload_absen(), format="multipart")
        mock_now.return_value = timezone.make_aware(dt.combine(self.hari_ini, dt_time(8, 30)))
        resp = self.client.post("/api/presensi/pulang", _payload_absen(), format="multipart")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["diterima"])
        self.assertTrue(
            Presensi.objects.filter(user=self.user, waktu_pulang__isnull=False).exists()
        )

    @patch("presensi.views.verifikasi_wajah")
    @patch("presensi.views.timezone.now")
    def test_lembur_lebih_dari_ambang_wajib_keterangan(self, mock_now, mock_verifikasi):
        mock_verifikasi.return_value = HasilCekWajah(True, None, 0.95)
        mock_now.return_value = timezone.make_aware(dt.combine(self.hari_ini, dt_time(8, 0)))
        self.client.post("/api/presensi/masuk", _payload_absen(), format="multipart")

        # Kelompok "Dosen" (seed migrasi) jam_pulang 14:00 -- pulang jam
        # 17:00 = 180 menit lembur, di atas ambang wajib keterangan (120 menit).
        mock_now.return_value = timezone.make_aware(dt.combine(self.hari_ini, dt_time(17, 0)))
        resp = self.client.post("/api/presensi/pulang", _payload_absen(), format="multipart")
        self.assertFalse(resp.data["diterima"])
        self.assertEqual(resp.data["alasan"], "keterangan_lembur_wajib")
        self.assertIsNone(Presensi.objects.get(user=self.user).waktu_pulang)

    @patch("presensi.views.verifikasi_wajah")
    @patch("presensi.views.timezone.now")
    def test_lembur_dengan_keterangan_diterima_dan_menunggu_persetujuan(self, mock_now, mock_verifikasi):
        mock_verifikasi.return_value = HasilCekWajah(True, None, 0.95)
        mock_now.return_value = timezone.make_aware(dt.combine(self.hari_ini, dt_time(8, 0)))
        self.client.post("/api/presensi/masuk", _payload_absen(), format="multipart")

        mock_now.return_value = timezone.make_aware(dt.combine(self.hari_ini, dt_time(17, 0)))
        resp = self.client.post(
            "/api/presensi/pulang", _payload_absen(keterangan_lembur="Rapat mendadak"), format="multipart",
        )
        self.assertTrue(resp.data["diterima"])
        self.assertTrue(resp.data["perlu_persetujuan_lembur"])
        presensi = Presensi.objects.get(user=self.user)
        self.assertEqual(presensi.status_lembur, StatusApprovalLembur.MENUNGGU)
        self.assertEqual(presensi.keterangan_lembur, "Rapat mendadak")
        self.assertEqual(presensi.menit_lembur, 180)

    @patch("presensi.views.verifikasi_wajah")
    @patch("presensi.views.timezone.now")
    def test_lembur_di_bawah_ambang_otomatis_diterima_tanpa_keterangan(self, mock_now, mock_verifikasi):
        mock_verifikasi.return_value = HasilCekWajah(True, None, 0.95)
        mock_now.return_value = timezone.make_aware(dt.combine(self.hari_ini, dt_time(8, 0)))
        self.client.post("/api/presensi/masuk", _payload_absen(), format="multipart")

        # 90 menit lembur -- di bawah ambang 120 menit, tidak perlu keterangan.
        mock_now.return_value = timezone.make_aware(dt.combine(self.hari_ini, dt_time(15, 30)))
        resp = self.client.post("/api/presensi/pulang", _payload_absen(), format="multipart")
        self.assertTrue(resp.data["diterima"])
        self.assertFalse(resp.data["perlu_persetujuan_lembur"])
        presensi = Presensi.objects.get(user=self.user)
        self.assertEqual(presensi.menit_lembur, 90)
        self.assertEqual(presensi.status_lembur, StatusApprovalLembur.TIDAK_ADA)


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


class ParafDosenAPITest(APITestCase):
    """Endpoint POST /api/presensi/paraf -- simpan/ganti paraf digital."""

    def setUp(self):
        self.user = _buat_dosen_user()
        self.client.force_authenticate(user=self.user)

    def test_simpan_paraf_baru(self):
        resp = self.client.post(
            "/api/presensi/paraf", {"gambar": _foto_palsu("paraf.png")}, format="multipart",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["status"], "ok")
        self.assertTrue(ParafDosen.objects.filter(user=self.user).exists())

    def test_ganti_paraf_yang_sudah_ada(self):
        self.client.post("/api/presensi/paraf", {"gambar": _foto_palsu("paraf1.png")}, format="multipart")
        paraf_pertama = ParafDosen.objects.get(user=self.user)
        nama_file_pertama = paraf_pertama.gambar.name

        self.client.post("/api/presensi/paraf", {"gambar": _foto_palsu("paraf2.png")}, format="multipart")
        self.assertEqual(ParafDosen.objects.filter(user=self.user).count(), 1)
        paraf_pertama.refresh_from_db()
        self.assertNotEqual(paraf_pertama.gambar.name, nama_file_pertama)

    def test_tanpa_gambar_ditolak(self):
        resp = self.client.post("/api/presensi/paraf", {}, format="multipart")
        self.assertEqual(resp.status_code, 400)

    def test_tanpa_autentikasi_ditolak(self):
        self.client.force_authenticate(user=None)
        resp = self.client.post(
            "/api/presensi/paraf", {"gambar": _foto_palsu("paraf.png")}, format="multipart",
        )
        self.assertEqual(resp.status_code, 401)


class HalamanParafViewTest(TestCase):
    """Halaman web /presensi/paraf/."""

    def setUp(self):
        self.user = _buat_dosen_user()

    def test_tanpa_login_dialihkan(self):
        resp = self.client.get("/presensi/paraf/")
        self.assertEqual(resp.status_code, 302)

    def test_sudah_login_bisa_akses_tanpa_paraf(self):
        self.client.force_login(self.user)
        resp = self.client.get("/presensi/paraf/")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context["paraf"])

    def test_menampilkan_paraf_tersimpan(self):
        ParafDosen.objects.create(user=self.user, gambar=_foto_palsu("paraf.png"))
        self.client.force_login(self.user)
        resp = self.client.get("/presensi/paraf/")
        self.assertIsNotNone(resp.context["paraf"])


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


class PutuskanLemburViewTest(TestCase):
    """Persetujuan keterangan lembur oleh atasan -- ditolak berarti jam
    kerja terhitung dibatasi ke jam pulang normal (lihat Presensi.
    durasi_kerja_menit), tapi waktu_pulang ASLI tidak diubah."""

    def setUp(self):
        self.dosen = User.objects.create_user(
            username="lemburdosen", password="testpass123", role="dosen",
            nidn="7777777777", kode_prodi="TI", kode_fakultas="FT",
        )
        self.kelompok = KelompokPresensi.objects.create(
            nama="Dosen Test", roles=["dosen"], jam_masuk=dt_time(8, 0), jam_pulang=dt_time(14, 0),
        )
        self.tanggal = timezone.localdate()
        self.presensi = Presensi.objects.create(
            user=self.dosen, tanggal=self.tanggal, kelompok=self.kelompok,
            waktu_masuk=timezone.make_aware(dt.combine(self.tanggal, dt_time(8, 0))),
            waktu_pulang=timezone.make_aware(dt.combine(self.tanggal, dt_time(17, 0))),
            menit_lembur=180, keterangan_lembur="Rapat mendadak",
            status_lembur=StatusApprovalLembur.MENUNGGU,
        )

    def test_dosen_biasa_tidak_bisa_akses(self):
        self.client.force_login(self.dosen)
        resp = self.client.post(f"/presensi/tinjau/{self.presensi.id}/putuskan-lembur/", {"aksi": "setujui"})
        self.assertEqual(resp.status_code, 403)

    def test_setujui_lembur_menghitung_penuh_jam_kerja(self):
        admin = User.objects.create_user(username="lemburadmin", password="testpass123", role="admin")
        self.client.force_login(admin)
        resp = self.client.post(f"/presensi/tinjau/{self.presensi.id}/putuskan-lembur/", {"aksi": "setujui"})
        self.assertEqual(resp.status_code, 302)
        self.presensi.refresh_from_db()
        self.assertEqual(self.presensi.status_lembur, StatusApprovalLembur.DISETUJUI)
        self.assertEqual(self.presensi.approver_lembur, admin)
        self.assertIsNotNone(self.presensi.waktu_keputusan_lembur)
        self.assertEqual(self.presensi.durasi_kerja_menit, 540)  # 08.00-17.00 penuh

    def test_tolak_lembur_membatasi_jam_kerja_ke_normal(self):
        admin = User.objects.create_user(username="lemburadmin2", password="testpass123", role="admin")
        self.client.force_login(admin)
        resp = self.client.post(f"/presensi/tinjau/{self.presensi.id}/putuskan-lembur/", {"aksi": "tolak"})
        self.assertEqual(resp.status_code, 302)
        self.presensi.refresh_from_db()
        self.assertEqual(self.presensi.status_lembur, StatusApprovalLembur.DITOLAK)
        # waktu_pulang ASLI tidak diubah, cuma jam kerja terhitung yang dibatasi.
        # localtime() wajib di sini -- setelah roundtrip DB, Django kembalikan
        # datetime UTC, bukan waktu lokal (WITA) yang aslinya di-set.
        self.assertEqual(timezone.localtime(self.presensi.waktu_pulang).time(), dt_time(17, 0))
        self.assertEqual(self.presensi.durasi_kerja_menit, 360)  # dibatasi ke 08.00-14.00

    def test_kaprodi_tidak_bisa_putuskan_lembur_di_luar_prodi(self):
        kaprodi = User.objects.create_user(
            username="lemburkaprodi", password="testpass123", role="kaprodi", kode_prodi="SI",
        )
        self.client.force_login(kaprodi)
        resp = self.client.post(f"/presensi/tinjau/{self.presensi.id}/putuskan-lembur/", {"aksi": "setujui"})
        self.assertEqual(resp.status_code, 403)
        self.presensi.refresh_from_db()
        self.assertEqual(self.presensi.status_lembur, StatusApprovalLembur.MENUNGGU)


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
        # menit_terlambat di-set eksplisit, sesuai yang seharusnya sudah
        # dihitung & disimpan AbsenMasukView saat absen masuk sungguhan
        # (lihat presensi/decision.py::hitung_ketepatan_masuk) -- bukan
        # dihitung ulang dari lokasi.jam_masuk di top_telat_hari_ini lagi.
        waktu_a = timezone.make_aware(dt.combine(self.hari_ini, dt_time(8, 10)))
        waktu_b = timezone.make_aware(dt.combine(self.hari_ini, dt_time(8, 40)))
        Presensi.objects.create(
            user=self.dosen_a, tanggal=self.hari_ini, status=StatusPresensi.TELAT,
            waktu_masuk=waktu_a, lokasi=self.lokasi, menit_terlambat=10,
        )
        Presensi.objects.create(
            user=self.dosen_b, tanggal=self.hari_ini, status=StatusPresensi.TELAT,
            waktu_masuk=waktu_b, lokasi=self.lokasi, menit_terlambat=40,
        )
        top = top_telat_hari_ini(self.user_ids, tanggal=self.hari_ini)
        self.assertEqual(len(top), 2)
        self.assertEqual(top[0]["presensi"].user_id, self.dosen_b.id)  # paling telat duluan
        self.assertEqual(top[0]["menit_telat"], 40)
        self.assertEqual(top[1]["menit_telat"], 10)

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


class LaporanBulananViewTest(TestCase):
    """Halaman /presensi/laporan-bulanan/ -- BEDA dari /presensi/data/
    (dosen-only lewat get_dosen_queryset), di sini lintas-pegawai (dosen +
    staf/tendik), discope lewat dapat_kelola sama seperti /presensi/tinjau/."""

    def setUp(self):
        self.dosen = User.objects.create_user(
            username="lapdosen", password="testpass123", role="dosen",
            nidn="8888888888", kode_fakultas="FT", kode_prodi="TI",
        )
        self.staf = User.objects.create_user(
            username="lapstaf", password="testpass123", role="tendik", kode_fakultas="FT",
        )
        self.kelompok_dosen = KelompokPresensi.objects.get(nama="Dosen")
        self.hari_ini = timezone.localdate()
        Presensi.objects.create(
            user=self.dosen, tanggal=self.hari_ini, kelompok=self.kelompok_dosen,
            waktu_masuk=timezone.make_aware(dt.combine(self.hari_ini, dt_time(8, 0))),
            waktu_pulang=timezone.make_aware(dt.combine(self.hari_ini, dt_time(14, 0))),
        )
        Presensi.objects.create(
            user=self.staf, tanggal=self.hari_ini,
            waktu_masuk=timezone.make_aware(dt.combine(self.hari_ini, dt_time(8, 0))),
            waktu_pulang=timezone.make_aware(dt.combine(self.hari_ini, dt_time(16, 0))),
        )

    def test_dosen_biasa_tidak_bisa_akses(self):
        self.client.force_login(self.dosen)
        resp = self.client.get("/presensi/laporan-bulanan/")
        self.assertEqual(resp.status_code, 403)

    def test_admin_melihat_dosen_dan_staf(self):
        admin = User.objects.create_user(username="lapadmin", password="testpass123", role="admin")
        self.client.force_login(admin)
        resp = self.client.get(f"/presensi/laporan-bulanan/?bulan={self.hari_ini.month}&tahun={self.hari_ini.year}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "lapdosen")
        self.assertContains(resp, "lapstaf")

    def test_total_jam_kerja_tampil_format_jam_menit(self):
        admin = User.objects.create_user(username="lapadmin2", password="testpass123", role="admin")
        self.client.force_login(admin)
        resp = self.client.get(f"/presensi/laporan-bulanan/?bulan={self.hari_ini.month}&tahun={self.hari_ini.year}")
        self.assertContains(resp, "06:00")  # dosen: 08.00-14.00
        self.assertContains(resp, "08:00")  # staf: 08.00-16.00

    def test_kaprodi_hanya_melihat_prodi_sendiri(self):
        kaprodi = User.objects.create_user(
            username="lapkaprodi", password="testpass123", role="kaprodi", kode_prodi="TI",
        )
        self.client.force_login(kaprodi)
        resp = self.client.get(f"/presensi/laporan-bulanan/?bulan={self.hari_ini.month}&tahun={self.hari_ini.year}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "lapdosen")
        self.assertNotContains(resp, "lapstaf")

    def test_bulan_tanpa_presensi_kosong(self):
        admin = User.objects.create_user(username="lapadmin3", password="testpass123", role="admin")
        self.client.force_login(admin)
        bulan_lalu = self.hari_ini.month - 1 or 12
        resp = self.client.get(f"/presensi/laporan-bulanan/?bulan={bulan_lalu}&tahun={self.hari_ini.year}")
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "lapdosen")

    def test_dosen_biasa_tidak_bisa_ekspor(self):
        self.client.force_login(self.dosen)
        resp = self.client.get("/presensi/laporan-bulanan/ekspor/")
        self.assertEqual(resp.status_code, 403)

    def test_admin_bisa_ekspor_excel(self):
        admin = User.objects.create_user(username="lapekspor", password="testpass123", role="admin")
        self.client.force_login(admin)
        resp = self.client.get(f"/presensi/laporan-bulanan/ekspor/?bulan={self.hari_ini.month}&tahun={self.hari_ini.year}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


class PengaturanKelompokViewTest(TestCase):
    """Halaman /presensi/pengaturan/kelompok/ -- admin-only (BEDA dengan
    Tinjau Presensi yang di-scope fakultas/prodi, ini institusi-wide)."""

    def setUp(self):
        self.admin = User.objects.create_user(username="pengaturanadmin", password="testpass123", role="admin")
        self.dekan = User.objects.create_user(username="pengaturandekan", password="testpass123", role="dekan")
        self.kelompok = KelompokPresensi.objects.get(nama="Dosen")

    def test_dekan_tidak_bisa_akses(self):
        self.client.force_login(self.dekan)
        resp = self.client.get("/presensi/pengaturan/kelompok/")
        self.assertEqual(resp.status_code, 403)

    def test_admin_bisa_lihat_daftar(self):
        self.client.force_login(self.admin)
        resp = self.client.get("/presensi/pengaturan/kelompok/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Dosen")
        self.assertContains(resp, "Pejabat")
        self.assertContains(resp, "Staf/Tendik")

    def test_admin_bisa_tambah_kelompok(self):
        self.client.force_login(self.admin)
        resp = self.client.post("/presensi/pengaturan/kelompok/tambah/", {
            "nama": "Kelompok Uji",
            "roles": ["operator"],
            "hari_kerja": ["0", "1", "2", "3", "4"],
            "jam_masuk": "09:00",
            "jam_pulang": "17:00",
            "toleransi_menit": "10",
            "aktif": "on",
        })
        self.assertEqual(resp.status_code, 302)
        baru = KelompokPresensi.objects.get(nama="Kelompok Uji")
        self.assertEqual(baru.roles, ["operator"])
        self.assertEqual(sorted(baru.hari_kerja), [0, 1, 2, 3, 4])

    def test_admin_bisa_ubah_kelompok(self):
        self.client.force_login(self.admin)
        resp = self.client.post(f"/presensi/pengaturan/kelompok/{self.kelompok.id}/ubah/", {
            "nama": "Dosen",
            "roles": ["dosen"],
            "hari_kerja": ["0", "1", "2", "3", "4", "5"],
            "jam_masuk": "07:30",
            "jam_pulang": "14:00",
            "toleransi_menit": "20",
            "aktif": "on",
        })
        self.assertEqual(resp.status_code, 302)
        self.kelompok.refresh_from_db()
        self.assertEqual(self.kelompok.jam_masuk, dt_time(7, 30))
        self.assertEqual(self.kelompok.toleransi_menit, 20)

    def test_admin_bisa_toggle_aktif(self):
        self.client.force_login(self.admin)
        self.assertTrue(self.kelompok.aktif)
        resp = self.client.post(f"/presensi/pengaturan/kelompok/{self.kelompok.id}/toggle-aktif/")
        self.assertEqual(resp.status_code, 302)
        self.kelompok.refresh_from_db()
        self.assertFalse(self.kelompok.aktif)

    def test_dekan_tidak_bisa_toggle_aktif(self):
        self.client.force_login(self.dekan)
        resp = self.client.post(f"/presensi/pengaturan/kelompok/{self.kelompok.id}/toggle-aktif/")
        self.assertEqual(resp.status_code, 403)
        self.kelompok.refresh_from_db()
        self.assertTrue(self.kelompok.aktif)


class PengaturanHariLiburViewTest(TestCase):
    """Halaman /presensi/pengaturan/hari-libur/ -- admin-only."""

    def setUp(self):
        self.admin = User.objects.create_user(username="liburadmin", password="testpass123", role="admin")
        self.dosen = _buat_dosen_user(nidn="9999999999", username="liburdosen")

    def test_dosen_tidak_bisa_akses(self):
        self.client.force_login(self.dosen)
        resp = self.client.get("/presensi/pengaturan/hari-libur/")
        self.assertEqual(resp.status_code, 403)

    def test_admin_bisa_tambah_dan_lihat(self):
        self.client.force_login(self.admin)
        resp = self.client.post("/presensi/pengaturan/hari-libur/tambah/", {
            "tanggal": "2026-08-17", "keterangan": "HUT RI", "jenis": "nasional",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(HariLibur.objects.filter(tanggal="2026-08-17", keterangan="HUT RI").exists())

        resp = self.client.get("/presensi/pengaturan/hari-libur/")
        self.assertContains(resp, "HUT RI")

    def test_admin_bisa_hapus(self):
        libur = HariLibur.objects.create(tanggal="2026-12-25", keterangan="Natal", jenis="nasional")
        self.client.force_login(self.admin)
        resp = self.client.post(f"/presensi/pengaturan/hari-libur/{libur.id}/hapus/")
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(HariLibur.objects.filter(id=libur.id).exists())


class PengaturanTargetViewTest(TestCase):
    """Halaman /presensi/pengaturan/target/ -- admin-only."""

    def setUp(self):
        self.admin = User.objects.create_user(username="targetadmin", password="testpass123", role="admin")
        self.dosen = _buat_dosen_user(nidn="8888888880", username="targetdosen")
        self.kelompok = KelompokPresensi.objects.get(nama="Dosen")

    def test_dosen_tidak_bisa_akses(self):
        self.client.force_login(self.dosen)
        resp = self.client.get("/presensi/pengaturan/target/")
        self.assertEqual(resp.status_code, 403)

    def test_admin_bisa_tambah_target(self):
        self.client.force_login(self.admin)
        resp = self.client.post("/presensi/pengaturan/target/tambah/", {
            "kelompok": self.kelompok.id, "bulan": "8", "tahun": "2026",
            "target_hari_kerja": "24", "target_jam_kerja": "144",
        })
        self.assertEqual(resp.status_code, 302)
        target = TargetKerjaBulanan.objects.get(kelompok=self.kelompok, bulan=8, tahun=2026)
        self.assertEqual(target.target_hari_kerja, 24)
        self.assertEqual(target.nama_bulan, "Agustus")

    def test_target_duplikat_kelompok_bulan_tahun_ditolak(self):
        TargetKerjaBulanan.objects.create(
            kelompok=self.kelompok, bulan=9, tahun=2026, target_hari_kerja=24, target_jam_kerja=144,
        )
        self.client.force_login(self.admin)
        resp = self.client.post("/presensi/pengaturan/target/tambah/", {
            "kelompok": self.kelompok.id, "bulan": "9", "tahun": "2026",
            "target_hari_kerja": "20", "target_jam_kerja": "120",
        })
        self.assertEqual(resp.status_code, 200)  # form invalid, render ulang bukan redirect
        self.assertEqual(TargetKerjaBulanan.objects.filter(kelompok=self.kelompok, bulan=9, tahun=2026).count(), 1)

    def test_admin_bisa_ubah_dan_hapus_target(self):
        target = TargetKerjaBulanan.objects.create(
            kelompok=self.kelompok, bulan=10, tahun=2026, target_hari_kerja=24, target_jam_kerja=144,
        )
        self.client.force_login(self.admin)
        resp = self.client.post(f"/presensi/pengaturan/target/{target.id}/ubah/", {
            "kelompok": self.kelompok.id, "bulan": "10", "tahun": "2026",
            "target_hari_kerja": "22", "target_jam_kerja": "132",
        })
        self.assertEqual(resp.status_code, 302)
        target.refresh_from_db()
        self.assertEqual(target.target_hari_kerja, 22)

        resp = self.client.post(f"/presensi/pengaturan/target/{target.id}/hapus/")
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(TargetKerjaBulanan.objects.filter(id=target.id).exists())


class TopTelatMenitTerlambatTest(TestCase):
    """top_telat_hari_ini sekarang pakai Presensi.menit_terlambat yang
    tersimpan (kelompok-aware), bukan dihitung ulang dari lokasi saja."""

    def test_menit_telat_ambil_dari_field_tersimpan(self):
        dosen = _buat_dosen_user(nidn="7777777771", username="topmenitdosen")
        lokasi = LokasiKantor.objects.create(nama="Kampus", latitude=0.0, longitude=0.0)
        hari_ini = timezone.localdate()
        Presensi.objects.create(
            user=dosen, tanggal=hari_ini, status=StatusPresensi.TELAT,
            waktu_masuk=timezone.now(), lokasi=lokasi, menit_terlambat=99,
        )
        top = top_telat_hari_ini([dosen.id], tanggal=hari_ini)
        self.assertEqual(top[0]["menit_telat"], 99)


class HalamanRiwayatTest(TestCase):
    """Riwayat presensi pribadi -- gabungan Presensi & IzinCuti disetujui,
    milik SENDIRI saja."""

    def setUp(self):
        self.user = _buat_dosen_user()
        self.hari_ini = timezone.localdate()

    def test_tanpa_login_dialihkan(self):
        resp = self.client.get("/presensi/riwayat/")
        self.assertEqual(resp.status_code, 302)

    def test_menampilkan_presensi_dan_izin_disetujui_milik_sendiri(self):
        Presensi.objects.create(user=self.user, tanggal=self.hari_ini, status=StatusPresensi.HADIR)
        IzinCuti.objects.create(
            user=self.user, tipe=IzinCuti.Tipe.DINAS,
            tanggal_mulai=self.hari_ini, tanggal_selesai=self.hari_ini,
            alasan="Seminar nasional", status=IzinCuti.StatusApproval.DISETUJUI,
        )
        self.client.force_login(self.user)
        resp = self.client.get("/presensi/riwayat/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Seminar nasional")

    def test_tidak_menampilkan_izin_yang_belum_disetujui(self):
        IzinCuti.objects.create(
            user=self.user, tipe=IzinCuti.Tipe.SAKIT,
            tanggal_mulai=self.hari_ini, tanggal_selesai=self.hari_ini,
            alasan="Demam tinggi", status=IzinCuti.StatusApproval.MENUNGGU,
        )
        self.client.force_login(self.user)
        resp = self.client.get("/presensi/riwayat/")
        self.assertNotContains(resp, "Demam tinggi")

    def test_tidak_menampilkan_presensi_orang_lain(self):
        user_lain = _buat_dosen_user(nidn="6666666666", username="oranglain")
        Presensi.objects.create(user=user_lain, tanggal=self.hari_ini, status=StatusPresensi.HADIR)
        self.client.force_login(self.user)
        resp = self.client.get("/presensi/riwayat/")
        self.assertEqual(resp.context["entri"], [])


class HalamanIzinTest(TestCase):
    """Pengajuan izin/sakit/cuti/dinas mandiri."""

    def setUp(self):
        self.user = _buat_dosen_user()
        self.client.force_login(self.user)

    def test_tanpa_login_dialihkan(self):
        self.client.logout()
        resp = self.client.get("/presensi/izin/")
        self.assertEqual(resp.status_code, 302)

    def test_ajukan_izin_berhasil(self):
        resp = self.client.post("/presensi/izin/", {
            "tipe": "sakit",
            "tanggal_mulai": "2026-07-28",
            "tanggal_selesai": "2026-07-28",
            "alasan": "Demam tinggi",
        })
        self.assertEqual(resp.status_code, 302)
        izin = IzinCuti.objects.get(user=self.user)
        self.assertEqual(izin.status, IzinCuti.StatusApproval.MENUNGGU)
        self.assertEqual(izin.alasan, "Demam tinggi")

    def test_tanggal_selesai_sebelum_mulai_ditolak(self):
        resp = self.client.post("/presensi/izin/", {
            "tipe": "cuti",
            "tanggal_mulai": "2026-07-28",
            "tanggal_selesai": "2026-07-20",
            "alasan": "Test",
        })
        self.assertEqual(resp.status_code, 200)  # form dirender ulang dengan error
        self.assertFalse(IzinCuti.objects.filter(user=self.user).exists())

    def test_riwayat_pengajuan_sendiri_tampil(self):
        IzinCuti.objects.create(
            user=self.user, tipe=IzinCuti.Tipe.CUTI,
            tanggal_mulai="2026-07-01", tanggal_selesai="2026-07-02",
            alasan="Liburan keluarga",
        )
        resp = self.client.get("/presensi/izin/")
        self.assertContains(resp, "Liburan keluarga")


class TinjauIzinViewTest(TestCase):
    """Halaman atasan untuk menyetujui/menolak pengajuan izin -- akses &
    scoping sama seperti TinjauPresensiViewTest."""

    def setUp(self):
        self.dosen_a = User.objects.create_user(
            username="izinA", password="testpass123", role="dosen",
            nidn="7777777777", kode_prodi="TI", kode_fakultas="FT",
        )
        self.dosen_b = User.objects.create_user(
            username="izinB", password="testpass123", role="dosen",
            nidn="8888888888", kode_prodi="SI", kode_fakultas="FT",
        )
        self.izin_a = IzinCuti.objects.create(
            user=self.dosen_a, tipe=IzinCuti.Tipe.SAKIT,
            tanggal_mulai="2026-07-28", tanggal_selesai="2026-07-28", alasan="Demam",
        )
        self.izin_b = IzinCuti.objects.create(
            user=self.dosen_b, tipe=IzinCuti.Tipe.CUTI,
            tanggal_mulai="2026-07-29", tanggal_selesai="2026-07-30", alasan="Liburan",
        )

    def test_dosen_biasa_tidak_bisa_akses(self):
        self.client.force_login(self.dosen_a)
        resp = self.client.get("/presensi/izin/tinjau/")
        self.assertEqual(resp.status_code, 403)

    def test_admin_melihat_semua_pengajuan_menunggu(self):
        admin = User.objects.create_user(username="izinadmin", password="testpass123", role="admin")
        self.client.force_login(admin)
        resp = self.client.get("/presensi/izin/tinjau/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Demam")
        self.assertContains(resp, "Liburan")

    def test_kaprodi_hanya_melihat_prodi_sendiri(self):
        kaprodi = User.objects.create_user(
            username="izinkaprodi", password="testpass123", role="kaprodi", kode_prodi="TI",
        )
        self.client.force_login(kaprodi)
        resp = self.client.get("/presensi/izin/tinjau/")
        self.assertContains(resp, "Demam")
        self.assertNotContains(resp, "Liburan")

    def test_setujui_izin(self):
        admin = User.objects.create_user(username="izinadmin2", password="testpass123", role="admin")
        self.client.force_login(admin)
        resp = self.client.post(f"/presensi/izin/tinjau/{self.izin_a.id}/putuskan/", {"aksi": "setujui"})
        self.assertEqual(resp.status_code, 302)
        self.izin_a.refresh_from_db()
        self.assertEqual(self.izin_a.status, IzinCuti.StatusApproval.DISETUJUI)
        self.assertEqual(self.izin_a.approver, admin)

    def test_tolak_izin(self):
        admin = User.objects.create_user(username="izinadmin3", password="testpass123", role="admin")
        self.client.force_login(admin)
        resp = self.client.post(f"/presensi/izin/tinjau/{self.izin_a.id}/putuskan/", {"aksi": "tolak"})
        self.assertEqual(resp.status_code, 302)
        self.izin_a.refresh_from_db()
        self.assertEqual(self.izin_a.status, IzinCuti.StatusApproval.DITOLAK)

    def test_kaprodi_tidak_bisa_putuskan_izin_di_luar_prodi(self):
        kaprodi = User.objects.create_user(
            username="izinkaprodi2", password="testpass123", role="kaprodi", kode_prodi="TI",
        )
        self.client.force_login(kaprodi)
        resp = self.client.post(f"/presensi/izin/tinjau/{self.izin_b.id}/putuskan/", {"aksi": "setujui"})
        self.assertEqual(resp.status_code, 403)
        self.izin_b.refresh_from_db()
        self.assertEqual(self.izin_b.status, IzinCuti.StatusApproval.MENUNGGU)
