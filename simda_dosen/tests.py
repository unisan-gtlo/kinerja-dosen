"""Test untuk simda_dosen -- SIMDA (koneksi 'simda') tidak selalu
tersedia saat test, jadi query ke sana di-mock (pola sama dengan
GetPejabatAktifTest/GetDosenByNidnTest di presensi/tests.py)."""
import datetime
from unittest.mock import MagicMock, Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError
from django.test import TestCase, Client

from accounts.models import User

from .forms import (
    DataTendikForm, ProfilSayaTendikForm, RiwayatPelatihanTendikForm,
    RiwayatPendidikanTendikForm, RiwayatPrestasiTendikForm,
)
from .models import DataTendik, RiwayatPelatihanTendik, RiwayatPendidikanTendik, RiwayatPrestasiTendik
from .utils import bisa_tambah_tridarma, get_or_create_unit_kerja


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

    @patch("simda_dosen.views.DataTendik")
    def test_avatar_foto_tampil_di_daftar(self, mock_cls):
        # Avatar foto profil di depan nama -- sama modelnya dengan Rekap
        # Data dosen (templates/dashboard/rekap.html): <img> kalau ada
        # foto, ikon ti-user-circle kalau tidak. Item daftar pakai Mock
        # BIASA (bukan MagicMock) -- MagicMock otomatis mengimplementasi
        # __getitem__, dan resolusi variabel Django ({{ t.foto }}) selalu
        # mencoba dictionary-lookup (`t['foto']`) LEBIH DULU sebelum
        # attribute-lookup (dicek lewat hasattr(type(t), '__getitem__'),
        # bukan instance) -- kalau MagicMock, itu selalu sukses dan
        # mengembalikan mock bersarang alih-alih nilai yang di-set,
        # bikin assertion di test ini salah lolos/gagal tanpa terdeteksi.
        dengan_foto = Mock(id=1, nama_lengkap="Punya Foto", nip_yayasan="", jabatan="",
                            unit_kerja_nama="", status_kepegawaian_nama="", is_active=True)
        dengan_foto.foto.url = "/media/tendik/foto/contoh.jpg"
        tanpa_foto = Mock(id=2, nama_lengkap="Tanpa Foto", nip_yayasan="", jabatan="",
                           unit_kerja_nama="", status_kepegawaian_nama="", is_active=True, foto=None)

        mock_qs = MagicMock()
        mock_cls.objects.using.return_value = mock_qs
        mock_qs.all.return_value = mock_qs
        mock_qs.order_by.return_value = [dengan_foto, tanpa_foto]

        self.client.force_login(self.admin)
        resp = self.client.get("/simda-dosen/tendik/")

        self.assertContains(resp, '<img src="/media/tendik/foto/contoh.jpg"')
        self.assertContains(resp, "ti-user-circle")

    def test_dosen_biasa_tidak_bisa_ekspor_pdf(self):
        self.client.force_login(self.dosen)
        resp = self.client.get("/simda-dosen/tendik/ekspor/pdf/")
        self.assertEqual(resp.status_code, 403)

    def test_dosen_biasa_tidak_bisa_ekspor_excel(self):
        self.client.force_login(self.dosen)
        resp = self.client.get("/simda-dosen/tendik/ekspor/excel/")
        self.assertEqual(resp.status_code, 403)

    @patch("simda_dosen.views.DataTendik")
    def test_admin_bisa_ekspor_pdf(self, mock_cls):
        mock_qs = MagicMock()
        mock_cls.objects.using.return_value = mock_qs
        mock_qs.all.return_value = mock_qs
        mock_qs.order_by.return_value = []

        self.client.force_login(self.admin)
        resp = self.client.get("/simda-dosen/tendik/ekspor/pdf/")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")

    @patch("simda_dosen.views.DataTendik")
    def test_admin_bisa_ekspor_excel(self, mock_cls):
        mock_qs = MagicMock()
        mock_cls.objects.using.return_value = mock_qs
        mock_qs.all.return_value = mock_qs
        mock_qs.order_by.return_value = []

        self.client.force_login(self.admin)
        resp = self.client.get("/simda-dosen/tendik/ekspor/excel/")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

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


class GetOrCreateUnitKerjaTest(TestCase):
    """get_or_create_unit_kerja() -- fitur "ketik langsung Unit Kerja yang
    belum ada di dropdown, otomatis tersimpan sebagai opsi baru" di form
    Kelola Data Tendik, mirror pola get_or_create_bidang_keahlian (Profil
    Dosen). SIMDA di-mock (koneksi 'simda' tidak selalu tersedia)."""

    def test_nama_kosong_return_none(self):
        self.assertIsNone(get_or_create_unit_kerja(''))
        self.assertIsNone(get_or_create_unit_kerja('   '))

    @patch("simda_dosen.utils.UnitKerja")
    def test_unit_kerja_sudah_ada_pakai_id_existing(self, mock_unit):
        existing = MagicMock(id=42)
        mock_unit.objects.using.return_value.filter.return_value.first.return_value = existing

        hasil = get_or_create_unit_kerja("Tata Usaha")

        self.assertEqual(hasil, 42)
        mock_unit.objects.using.return_value.create.assert_not_called()

    @patch("simda_dosen.utils.UnitKerja")
    def test_unit_kerja_belum_ada_dibuat_baru(self, mock_unit):
        mock_unit.objects.using.return_value.filter.return_value.first.return_value = None
        mock_unit.objects.using.return_value.filter.return_value.exists.return_value = False
        baru = MagicMock(id=99)
        mock_unit.objects.using.return_value.create.return_value = baru

        hasil = get_or_create_unit_kerja("Unit Kerja Baru")

        self.assertEqual(hasil, 99)
        mock_unit.objects.using.return_value.create.assert_called_once()
        kwargs = mock_unit.objects.using.return_value.create.call_args.kwargs
        self.assertEqual(kwargs["nama"], "Unit Kerja Baru")
        self.assertEqual(kwargs["jenis"], "administrasi")


class ProfilTendikAksesTest(TestCase):
    """Halaman Profil Tendik (detail_tendik + CRUD 3 riwayat) -- admin-
    only, gerbang sama dengan Kelola Data Tendik (_bisa_kelola_data_tendik).
    Satu view representatif per aksi (pola gerbangnya identik di
    ketiganya: Pendidikan/Pelatihan/Prestasi)."""

    def setUp(self):
        self.admin = User.objects.create_user(username="profiltendikadmin", password="testpass123", role="admin")
        self.dosen = User.objects.create_user(username="profiltendikdosen", password="testpass123", role="dosen")

    def test_dosen_biasa_tidak_bisa_akses_detail(self):
        self.client.force_login(self.dosen)
        resp = self.client.get("/simda-dosen/tendik/1/detail/")
        self.assertEqual(resp.status_code, 403)

    def test_dosen_biasa_tidak_bisa_tambah_riwayat_pendidikan(self):
        self.client.force_login(self.dosen)
        resp = self.client.post("/simda-dosen/tendik/1/riwayat-pendidikan/tambah/")
        self.assertEqual(resp.status_code, 403)

    def test_dosen_biasa_tidak_bisa_hapus_riwayat_pelatihan(self):
        self.client.force_login(self.dosen)
        resp = self.client.post("/simda-dosen/tendik/riwayat-pelatihan/1/hapus/")
        self.assertEqual(resp.status_code, 403)

    def test_dosen_biasa_tidak_bisa_ubah_riwayat_prestasi(self):
        self.client.force_login(self.dosen)
        resp = self.client.get("/simda-dosen/tendik/riwayat-prestasi/1/ubah/")
        self.assertEqual(resp.status_code, 403)

    @patch("simda_dosen.views.DataTendik")
    def test_admin_bisa_buka_detail_tendik(self, mock_cls):
        mock_qs = MagicMock(spec=["get", "filter", "all", "order_by"])
        mock_cls.objects.using.return_value = mock_qs
        mock_tendik = MagicMock(
            id=1, nama_lengkap="Contoh Tendik", jabatan="Staf TU",
            unit_kerja_nama="Tata Usaha", nip_yayasan="12345",
        )
        mock_tendik.riwayat_pendidikan.all.return_value = []
        mock_tendik.riwayat_pelatihan.all.return_value = []
        mock_tendik.riwayat_prestasi.all.return_value = []
        mock_qs.get.return_value = mock_tendik

        self.client.force_login(self.admin)
        resp = self.client.get("/simda-dosen/tendik/1/detail/")

        self.assertEqual(resp.status_code, 200)


class TambahTendikUnitKerjaBaruTest(TestCase):
    """tambah_tendik -- kalau field "Atau Ketik Unit Kerja Baru" diisi,
    dipakai (lewat get_or_create_unit_kerja) untuk override unit_kerja_id
    sebelum disimpan, bukan pilihan dropdown. DataTendik.save() di-patch
    langsung di kelasnya (bukan mock nama modul) -- Meta.model pada
    DataTendikForm sudah mengikat ke kelas asli saat class body
    dieksekusi, jadi patch nama di modul forms/views TIDAK memengaruhi
    instance yang dibuat form.save(); patch.object(DataTendik, 'save')
    mencegat method-nya langsung di kelas manapun instance-nya dibuat,
    supaya tidak benar-benar coba nulis ke koneksi 'simda' saat test."""

    def setUp(self):
        self.admin = User.objects.create_user(username="unitkerjabaruadmin", password="testpass123", role="admin")
        self.client = Client()
        self.client.login(username="unitkerjabaruadmin", password="testpass123")

    @patch("simda_dosen.views.get_or_create_unit_kerja")
    @patch("simda_dosen.forms.UnitKerja")
    @patch("simda_dosen.forms.AgamaPublik")
    @patch("simda_dosen.forms.GolonganPublik")
    @patch("simda_dosen.forms.StatusKepegawaianPublik")
    @patch("simda_dosen.forms.JenisKepegawaianPublik")
    @patch.object(DataTendik, "save", new=MagicMock())
    def test_unit_kerja_baru_dipakai_lewat_get_or_create(
        self, mock_jenis, mock_status, mock_golongan, mock_agama, mock_unit_form, mock_get_or_create,
    ):
        for m in (mock_unit_form, mock_jenis, mock_status, mock_golongan, mock_agama):
            m.objects.using.return_value.all.return_value = []
            m.objects.using.return_value.filter.return_value.order_by.return_value = []
        mock_get_or_create.return_value = 777

        self.client.post("/simda-dosen/tendik/tambah/", {
            "nama_lengkap": "Tendik Baru", "jenis_kelamin": "L",
            "unit_kerja_id": "", "unit_kerja_baru": "Unit Baru Ketikan Admin",
        })

        mock_get_or_create.assert_called_once_with("Unit Baru Ketikan Admin")


class CompressUploadedFileWiringTest(TestCase):
    """Semua field upload di Kelola Tendik (foto biodata + file_ijazah/
    file_sertifikat/file_bukti Riwayat) sekarang dikompres otomatis
    lewat compress_uploaded_file() sebelum disimpan -- pola yang sama
    dengan upload dokumen di role dosen (profil/views.py, kinerja/
    views.py). Test ini murni memverifikasi WIRING-nya (compress_
    uploaded_file benar-benar dipanggil dengan file yang diupload),
    bukan logika kompresinya sendiri (sudah jadi tanggung jawab
    simda_dosen/file_compress.py, dipakai bareng lintas app)."""

    def setUp(self):
        self.admin = User.objects.create_user(username="kompresadmin", password="testpass123", role="admin")
        self.tendik_user = User.objects.create_user(
            username="komprestendik", password="testpass123", role="tendik", nip_yayasan="5555",
        )

    def _file_gambar(self, name="foto.jpg"):
        return SimpleUploadedFile(name, b"isi-file-palsu", content_type="image/jpeg")

    @patch("simda_dosen.views.compress_uploaded_file")
    @patch("simda_dosen.forms.UnitKerja")
    @patch("simda_dosen.forms.AgamaPublik")
    @patch("simda_dosen.forms.GolonganPublik")
    @patch("simda_dosen.forms.StatusKepegawaianPublik")
    @patch("simda_dosen.forms.JenisKepegawaianPublik")
    @patch.object(DataTendik, "save", new=MagicMock())
    def test_tambah_tendik_kompres_foto(
        self, mock_jenis, mock_status, mock_golongan, mock_agama, mock_unit, mock_compress,
    ):
        for m in (mock_unit, mock_jenis, mock_status, mock_golongan, mock_agama):
            m.objects.using.return_value.all.return_value = []
            m.objects.using.return_value.filter.return_value.order_by.return_value = []
        mock_compress.return_value = "hasil-kompres"

        self.client.force_login(self.admin)
        file_foto = self._file_gambar()
        self.client.post("/simda-dosen/tendik/tambah/", {
            "nama_lengkap": "Tendik Foto", "jenis_kelamin": "L", "foto": file_foto,
        })

        mock_compress.assert_called_once()
        self.assertEqual(mock_compress.call_args[0][0].name, "foto.jpg")

    @patch("simda_dosen.views.compress_uploaded_file")
    @patch("simda_dosen.forms.AgamaPublik")
    @patch("simda_dosen.views.get_simda_tendik_or_none")
    @patch.object(DataTendik, "save", new=MagicMock())
    def test_simpan_profil_saya_tendik_kompres_foto(self, mock_get, mock_agama, mock_compress):
        mock_agama.objects.using.return_value.order_by.return_value = []
        mock_get.return_value = DataTendik(id=8, nama_lengkap="Nama Lama")
        mock_compress.return_value = "hasil-kompres"

        self.client.force_login(self.tendik_user)
        self.client.post("/simda-dosen/profil-riwayat-saya/simpan/", {
            "nama_lengkap": "Nama Baru", "foto": self._file_gambar(),
        })

        mock_compress.assert_called_once()

    @patch("simda_dosen.views.compress_uploaded_file")
    @patch("simda_dosen.views.get_simda_tendik_or_none")
    @patch("simda_dosen.views.DataTendik")
    @patch.object(RiwayatPendidikanTendik, "save", new=MagicMock())
    def test_tambah_riwayat_pendidikan_kompres_file_ijazah(self, mock_datatendik_cls, mock_get, mock_compress):
        mock_qs = MagicMock(spec=["get", "filter", "all", "order_by"])
        mock_datatendik_cls.objects.using.return_value = mock_qs
        mock_qs.get.return_value = MagicMock(id=5)
        mock_get.return_value = MagicMock(id=5)
        mock_compress.return_value = "hasil-kompres"

        self.client.force_login(self.tendik_user)
        self.client.post("/simda-dosen/tendik/5/riwayat-pendidikan/tambah/", {
            "jenjang": "S1", "institusi": "Contoh Univ",
            "file_ijazah": SimpleUploadedFile("ijazah.pdf", b"isi-pdf-palsu", content_type="application/pdf"),
        })

        mock_compress.assert_called_once()
        self.assertEqual(mock_compress.call_args[0][0].name, "ijazah.pdf")


class ProfilRiwayatSayaAksesTest(TestCase):
    """profil_riwayat_saya -- self-service Tendik (2026-08-04): tendik
    boleh isi Riwayat Pendidikan/Pelatihan/Prestasi milik SENDIRI
    (dicocokkan lewat nip_yayasan, lihat get_simda_tendik_or_none),
    TIDAK boleh kelola riwayat tendik lain lewat manipulasi tendik_id/
    riwayat_id di URL. Biodata TETAP admin-only (tidak disentuh)."""

    def setUp(self):
        self.tendik_user = User.objects.create_user(
            username="tendiksendiri", password="testpass123", role="tendik", nip_yayasan="1111",
        )
        self.dosen = User.objects.create_user(username="tendikdosen2", password="testpass123", role="dosen")

    def test_dosen_tidak_bisa_akses(self):
        self.client.force_login(self.dosen)
        resp = self.client.get("/simda-dosen/profil-riwayat-saya/")
        self.assertEqual(resp.status_code, 403)

    @patch("simda_dosen.views.get_simda_tendik_or_none")
    def test_nip_yayasan_tidak_cocok_redirect_dengan_pesan(self, mock_get):
        mock_get.return_value = None
        self.client.force_login(self.tendik_user)
        resp = self.client.get("/simda-dosen/profil-riwayat-saya/")
        self.assertEqual(resp.status_code, 302)

    @patch("simda_dosen.views.get_simda_tendik_or_none")
    def test_tendik_dengan_data_cocok_bisa_akses(self, mock_get):
        mock_tendik = MagicMock(
            id=5, nama_lengkap="Contoh Tendik", jabatan="Staf",
            unit_kerja_nama="TU", nip_yayasan="1111",
        )
        mock_tendik.riwayat_pendidikan.all.return_value = []
        mock_tendik.riwayat_pelatihan.all.return_value = []
        mock_tendik.riwayat_prestasi.all.return_value = []
        mock_get.return_value = mock_tendik

        self.client.force_login(self.tendik_user)
        resp = self.client.get("/simda-dosen/profil-riwayat-saya/")

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["mode_diri_sendiri"])

    @patch("simda_dosen.views.get_simda_tendik_or_none")
    @patch("simda_dosen.views.DataTendik")
    def test_tendik_tidak_bisa_tambah_riwayat_tendik_lain(self, mock_datatendik_cls, mock_get):
        # Tendik login dengan DataTendik id=5, coba tambah riwayat untuk
        # tendik id=99 (bukan miliknya) lewat manipulasi URL.
        mock_qs = MagicMock(spec=["get", "filter", "all", "order_by"])
        mock_datatendik_cls.objects.using.return_value = mock_qs
        mock_qs.get.return_value = MagicMock(id=99)
        mock_get.return_value = MagicMock(id=5)

        self.client.force_login(self.tendik_user)
        resp = self.client.post("/simda-dosen/tendik/99/riwayat-pendidikan/tambah/", {
            "jenjang": "S1", "institusi": "Contoh Univ",
        })

        self.assertEqual(resp.status_code, 403)

    @patch.object(RiwayatPendidikanTendik, "save", new=MagicMock())
    @patch("simda_dosen.views.get_simda_tendik_or_none")
    @patch("simda_dosen.views.DataTendik")
    def test_tendik_bisa_tambah_riwayat_milik_sendiri(self, mock_datatendik_cls, mock_get):
        mock_qs = MagicMock(spec=["get", "filter", "all", "order_by"])
        mock_datatendik_cls.objects.using.return_value = mock_qs
        mock_qs.get.return_value = MagicMock(id=5)
        mock_get.return_value = MagicMock(id=5)

        self.client.force_login(self.tendik_user)
        resp = self.client.post("/simda-dosen/tendik/5/riwayat-pendidikan/tambah/", {
            "jenjang": "S1", "institusi": "Contoh Univ",
        })

        self.assertEqual(resp.status_code, 302)
        self.assertNotEqual(resp.status_code, 403)


class SimpanProfilSayaTendikTest(TestCase):
    """simpan_profil_saya_tendik -- tendik bisa ubah data pokok sendiri
    termasuk foto (2026-08-04 lanjutan). Field kepegawaian/struktural/
    bank TETAP admin-only: ProfilSayaTendikForm.Meta.fields = DataTendik.
    SELF_SERVICE_FIELDS, jadi field di luar itu tidak pernah tersentuh
    walau ikut dikirim di POST (bukan cuma diabaikan tampilannya)."""

    def setUp(self):
        self.tendik_user = User.objects.create_user(
            username="biodatatendik", password="testpass123", role="tendik", nip_yayasan="2222",
        )
        self.dosen = User.objects.create_user(username="biodatadosen", password="testpass123", role="dosen")

    def test_dosen_tidak_bisa_akses(self):
        self.client.force_login(self.dosen)
        resp = self.client.post("/simda-dosen/profil-riwayat-saya/simpan/")
        self.assertEqual(resp.status_code, 403)

    @patch("simda_dosen.views.get_simda_tendik_or_none")
    def test_nip_yayasan_tidak_cocok_redirect(self, mock_get):
        mock_get.return_value = None
        self.client.force_login(self.tendik_user)
        resp = self.client.post("/simda-dosen/profil-riwayat-saya/simpan/", {"nama_lengkap": "Coba"})
        self.assertEqual(resp.status_code, 302)

    @patch.object(DataTendik, "save", new=MagicMock())
    @patch("simda_dosen.forms.AgamaPublik")
    @patch("simda_dosen.views.get_simda_tendik_or_none")
    def test_tendik_bisa_ubah_biodata_sendiri_field_admin_tidak_ikut_berubah(self, mock_get, mock_agama):
        mock_agama.objects.using.return_value.order_by.return_value = []
        real_tendik = DataTendik(id=7, nama_lengkap="Nama Lama")
        mock_get.return_value = real_tendik

        self.client.force_login(self.tendik_user)
        resp = self.client.post("/simda-dosen/profil-riwayat-saya/simpan/", {
            "nama_lengkap": "Nama Baru", "jenis_kelamin": "L",
            "unit_kerja_id": "999", "nip": "SIAPAPUN",
        })

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(real_tendik.nama_lengkap, "Nama Baru")
        self.assertIsNone(real_tendik.unit_kerja_id)
        self.assertEqual(real_tendik.nip, "")


class ProfilSayaTendikFormAgamaKosongTest(TestCase):
    """Bug fix 2026-08-05: Server Error 500 nyata di produksi saat tendik
    simpan Biodata Saya dengan Agama dikosongkan --
    'ValueError: Field agama_id expected a number but got ''.'.
    Penyebabnya forms.TypedChoiceField(coerce=int, ...) TANPA
    empty_value=None -- default bawaan Django (empty_value='') bikin
    _coerce() mengembalikan STRING KOSONG (bukan None) saat field
    dikosongkan, padahal model field-nya IntegerField(null=True). Test
    lama (test_tendik_bisa_ubah_biodata_sendiri_field_admin_tidak_ikut_
    berubah) tidak menangkap ini karena DataTendik.save() di-mock total
    -- write ke DB yang sesungguhnya (tempat ValueError-nya muncul) tidak
    pernah benar-benar dijalankan di situ. Test ini murni level Form,
    tanpa panggil .save(), supaya cepat & tidak butuh mock DB tapi tetap
    menangkap kelas bug ini kalau terulang."""

    @patch("simda_dosen.forms.AgamaPublik")
    def test_agama_dikosongkan_menghasilkan_none_bukan_string_kosong(self, mock_agama):
        mock_agama.objects.using.return_value.order_by.return_value = []
        form = ProfilSayaTendikForm(data={"nama_lengkap": "Contoh Tendik", "agama_id": ""})

        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data["agama_id"])

    @patch("simda_dosen.forms.AgamaPublik")
    @patch("simda_dosen.forms.UnitKerja")
    @patch("simda_dosen.forms.JenisKepegawaianPublik")
    @patch("simda_dosen.forms.StatusKepegawaianPublik")
    @patch("simda_dosen.forms.GolonganPublik")
    def test_dropdown_admin_dikosongkan_juga_menghasilkan_none(
        self, mock_golongan, mock_status, mock_jenis, mock_unit, mock_agama,
    ):
        # Bug pattern yang sama ada di 5 TypedChoiceField DataTendikForm
        # (dipakai admin lewat Tambah/Ubah Tendik), bukan cuma agama_id
        # di ProfilSayaTendikForm -- ikut diverifikasi supaya tidak
        # terulang lagi kalau ada TypedChoiceField baru ditambahkan.
        for mock_ref in (mock_unit, mock_jenis, mock_status, mock_golongan, mock_agama):
            mock_ref.objects.using.return_value.filter.return_value.order_by.return_value = []
            mock_ref.objects.using.return_value.all.return_value = []
            mock_ref.objects.using.return_value.order_by.return_value = []

        form = DataTendikForm(data={
            "nama_lengkap": "Contoh Tendik", "jenis_kelamin": "L",
            "unit_kerja_id": "", "jenis_kepegawaian_id": "", "status_kepegawaian_id": "",
            "golongan_id": "", "agama_id": "",
        })

        self.assertTrue(form.is_valid(), form.errors)
        for field in ("unit_kerja_id", "jenis_kepegawaian_id", "status_kepegawaian_id", "golongan_id", "agama_id"):
            self.assertIsNone(form.cleaned_data[field], f"{field} seharusnya None, bukan string kosong")


class TendikDateInputFormatTest(TestCase):
    """Bug fix 2026-08-05: field bertipe tanggal (Tanggal Lahir, Tanggal
    Mulai Kerja, Tanggal SK Pengangkatan, Tanggal Mulai/Selesai Pelatihan)
    di Kelola Tendik terlihat KOSONG saat form dibuka untuk diedit,
    walau datanya tersimpan benar di database -- kalau admin/tendik lalu
    submit ulang form itu tanpa menyentuh field tanggalnya, nilai kosong
    tadi MENIMPA tanggal yang sudah benar jadi NULL ("tanggal tidak
    tersimpan").

    Akar masalah: `forms.DateInput(attrs={"type": "date"})` TANPA
    `format="%Y-%m-%d"` merender value existing pakai format locale
    id-id ("25-12-1985"), yang TIDAK valid untuk value <input
    type="date"> HTML5 (harus persis ISO 8601) -- browser menampilkan
    field itu kosong. `settings.DATE_INPUT_FORMATS` TIDAK bisa dipakai
    untuk memperbaiki ini (dicoba & diverifikasi TIDAK berpengaruh --
    locale module id-id selalu menang atas setting global selama l10n
    aktif, lihat riwayat percakapan), jadi diperbaiki dengan
    `format="%Y-%m-%d"` eksplisit di tiap widget."""

    @patch("simda_dosen.forms.AgamaPublik")
    def test_profil_saya_tendik_tgl_lahir_render_iso(self, mock_agama):
        mock_agama.objects.using.return_value.order_by.return_value = []
        tendik = DataTendik(id=1, nama_lengkap="Contoh", tgl_lahir=datetime.date(1985, 12, 25))
        form = ProfilSayaTendikForm(instance=tendik)

        self.assertEqual(form["tgl_lahir"].value(), "1985-12-25")

    @patch("simda_dosen.forms.AgamaPublik")
    @patch("simda_dosen.forms.UnitKerja")
    @patch("simda_dosen.forms.JenisKepegawaianPublik")
    @patch("simda_dosen.forms.StatusKepegawaianPublik")
    @patch("simda_dosen.forms.GolonganPublik")
    def test_data_tendik_form_semua_field_tanggal_render_iso(
        self, mock_golongan, mock_status, mock_jenis, mock_unit, mock_agama,
    ):
        for mock_ref in (mock_unit, mock_jenis, mock_status, mock_golongan, mock_agama):
            mock_ref.objects.using.return_value.filter.return_value.order_by.return_value = []
            mock_ref.objects.using.return_value.all.return_value = []
            mock_ref.objects.using.return_value.order_by.return_value = []

        tendik = DataTendik(
            id=1, nama_lengkap="Contoh",
            tgl_lahir=datetime.date(1985, 12, 25),
            tgl_mulai_kerja=datetime.date(2010, 1, 15),
            tgl_sk_pengangkatan=datetime.date(2010, 1, 1),
        )
        form = DataTendikForm(instance=tendik)

        self.assertEqual(form["tgl_lahir"].value(), "1985-12-25")
        self.assertEqual(form["tgl_mulai_kerja"].value(), "2010-01-15")
        self.assertEqual(form["tgl_sk_pengangkatan"].value(), "2010-01-01")

    def test_riwayat_pelatihan_tendik_form_tanggal_render_iso(self):
        riwayat = RiwayatPelatihanTendik(
            id=1, tanggal_mulai=datetime.date(2020, 6, 1), tanggal_selesai=datetime.date(2020, 6, 5),
        )
        form = RiwayatPelatihanTendikForm(instance=riwayat)

        self.assertEqual(form["tanggal_mulai"].value(), "2020-06-01")
        self.assertEqual(form["tanggal_selesai"].value(), "2020-06-05")


class RiwayatTendikLinkDriveFormTest(TestCase):
    """Fitur "Link Google Drive" (alternatif upload file) 2026-08-05 --
    field link_ijazah/link_sertifikat/link_bukti ditambahkan ke 3
    ModelForm Riwayat Tendik (Meta.fields), berdampingan dengan file_*
    yang sudah ada. Murni unit test level Form (is_valid/cleaned_data),
    tidak butuh koneksi 'simda' sungguhan karena tidak memanggil .save()."""

    def test_riwayat_pendidikan_tendik_form_terima_link_ijazah(self):
        form = RiwayatPendidikanTendikForm(data={
            "jenjang": "S1", "institusi": "Universitas Contoh", "jurusan": "Manajemen",
            "tahun_masuk": "2010", "tahun_lulus": "2014", "no_ijazah": "12345",
            "link_ijazah": "https://drive.google.com/ijazah",
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["link_ijazah"], "https://drive.google.com/ijazah")

    def test_riwayat_pelatihan_tendik_form_terima_link_sertifikat(self):
        form = RiwayatPelatihanTendikForm(data={
            "nama_pelatihan": "Pelatihan Contoh", "penyelenggara": "Lembaga X", "tingkat": "Nasional",
            "link_sertifikat": "https://drive.google.com/sertifikat",
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["link_sertifikat"], "https://drive.google.com/sertifikat")

    def test_riwayat_prestasi_tendik_form_terima_link_bukti(self):
        form = RiwayatPrestasiTendikForm(data={
            "nama_prestasi": "Prestasi Contoh", "tingkat": "Nasional", "tahun": "2020",
            "link_bukti": "https://drive.google.com/bukti",
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["link_bukti"], "https://drive.google.com/bukti")
