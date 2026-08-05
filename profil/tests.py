from unittest.mock import patch, Mock

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


class LinkGoogleDriveDokumenTest(TestCase):
    """Fitur "Link Google Drive" (alternatif upload file) 2026-08-05 --
    dosen yang dokumennya sudah ada di Drive cukup tempel link, tidak
    wajib upload ulang. simpan_profil menulis 3 field BARU
    (link_ktp/link_npwp/link_sk_pengangkatan) ke DataDosen; tambah_/
    edit_pendidikan mereaktivasi 2 field yang SUDAH ADA di model tapi
    belum pernah dibaca/ditulis view maupun template (url_ijazah/
    url_transkrip). SIMDA di-mock penuh (tidak ada objek nyata yang
    ditulis ke koneksi 'simda') -- yang diuji murni bahwa value dari
    POST sampai ke instance yang benar sebelum .save() dipanggil."""

    def setUp(self):
        self.dosen = User.objects.create_user(
            username="dosen_link_drive", password="testpass123", role="dosen",
            nidn="8800000901",
        )
        self.client = Client()
        # force_login (bukan login) -- django-axes (AxesStandaloneBackend,
        # AUTHENTICATION_BACKENDS di config/settings.py) mewajibkan request
        # bukan None saat authenticate(), padahal Client.login() Django
        # TIDAK PERNAH mengirim request (lihat django/test/client.py). Ini
        # bug pre-existing yang memengaruhi SEMUA test client.login() di
        # seluruh aplikasi (bukan cuma di sini), force_login melewati
        # authenticate() sepenuhnya jadi aman dipakai di sini.
        self.client.force_login(self.dosen)

    @patch("profil.views.get_simda_dosen_or_none")
    def test_simpan_profil_menyimpan_link_ktp_npwp_sk_pengangkatan(self, mock_dosen_fn):
        profil_mock = Mock()
        mock_dosen_fn.return_value = profil_mock
        self.client.post(reverse("profil:simpan_profil"), {
            "link_ktp": "https://drive.google.com/ktp",
            "link_npwp": "https://drive.google.com/npwp",
            "link_sk_pengangkatan": "https://drive.google.com/sk",
        })
        self.assertEqual(profil_mock.link_ktp, "https://drive.google.com/ktp")
        self.assertEqual(profil_mock.link_npwp, "https://drive.google.com/npwp")
        self.assertEqual(profil_mock.link_sk_pengangkatan, "https://drive.google.com/sk")
        profil_mock.save.assert_called_once()

    @patch("profil.views.get_simda_dosen_or_none")
    def test_simpan_profil_link_kosong_disimpan_string_kosong(self, mock_dosen_fn):
        """Field opsional -- kalau tidak diisi sama sekali harus jadi
        string kosong (bukan crash / bukan None), konsisten dengan pola
        field link_/url_ lain yang sudah ada (npwp, no_hp, dst)."""
        profil_mock = Mock()
        mock_dosen_fn.return_value = profil_mock
        self.client.post(reverse("profil:simpan_profil"), {})
        self.assertEqual(profil_mock.link_ktp, "")
        self.assertEqual(profil_mock.link_npwp, "")
        self.assertEqual(profil_mock.link_sk_pengangkatan, "")

    @patch("profil.views.sync_pendidikan_terakhir")
    @patch("profil.views.RiwayatPendidikanDosen")
    @patch("profil.views.get_simda_dosen_or_none")
    def test_tambah_pendidikan_menyimpan_url_ijazah_dan_transkrip(self, mock_dosen_fn, mock_model, mock_sync):
        mock_dosen_fn.return_value = Mock(nidn=self.dosen.nidn)
        mock_instance = Mock()
        mock_model.return_value = mock_instance
        self.client.post(reverse("profil:tambah_pendidikan"), {
            "jenjang": "S1", "nama_pt": "Universitas Contoh", "bidang_ilmu": "Informatika",
            "tahun_masuk": "2010", "tahun_lulus": "2014", "no_ijazah": "12345",
            "url_ijazah": "https://drive.google.com/ijazah",
            "url_transkrip": "https://drive.google.com/transkrip",
        })
        _, kwargs = mock_model.call_args
        self.assertEqual(kwargs["url_ijazah"], "https://drive.google.com/ijazah")
        self.assertEqual(kwargs["url_transkrip"], "https://drive.google.com/transkrip")
        mock_instance.save.assert_called_once()

    @patch("profil.views.sync_pendidikan_terakhir")
    @patch("profil.views.dapat_kelola_nidn")
    @patch("profil.views.get_object_or_404")
    def test_edit_pendidikan_menyimpan_url_ijazah_dan_transkrip(self, mock_get_obj, mock_dapat_kelola, mock_sync):
        pend = Mock()
        pend.dosen.nidn = self.dosen.nidn
        mock_get_obj.return_value = pend
        mock_dapat_kelola.return_value = True
        self.client.post(reverse("profil:edit_pendidikan", args=[1]), {
            "jenjang": "S1", "nama_pt": "Universitas Contoh", "bidang_ilmu": "Informatika",
            "url_ijazah": "https://drive.google.com/ijazah2",
            "url_transkrip": "https://drive.google.com/transkrip2",
        })
        self.assertEqual(pend.url_ijazah, "https://drive.google.com/ijazah2")
        self.assertEqual(pend.url_transkrip, "https://drive.google.com/transkrip2")
        pend.save.assert_called_once()
