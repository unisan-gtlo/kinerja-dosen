from django.test import TestCase

from .models import User


class TambahUserNipYayasanTest(TestCase):
    """Field nip_yayasan & opsi role Tendik ditambahkan ke form Kelola
    User (dulu tidak ada sama sekali di template, cuma NIDN) -- dibutuhkan
    supaya akun tendik bisa dibuat & ditautkan ke data SIMDA
    (simda_dosen.DataTendik) lewat NIP Yayasan, lihat CLAUDE.md bagian
    Kelola Data Tendik."""

    def setUp(self):
        self.admin = User.objects.create_user(username="kelolauseradmin", password="testpass123", role="admin")

    def test_admin_bisa_buat_akun_tendik_dengan_nip_yayasan(self):
        self.client.force_login(self.admin)
        resp = self.client.post("/accounts/tambah-user/", {
            "username": "tendikbaru", "first_name": "Tendik", "last_name": "Baru",
            "email": "", "nidn": "", "nip_yayasan": "200001", "role": "tendik",
            "kode_fakultas": "", "kode_prodi": "", "no_hp": "", "password": "testpass123",
        })
        self.assertEqual(resp.status_code, 302)
        user = User.objects.get(username="tendikbaru")
        self.assertEqual(user.role, "tendik")
        self.assertEqual(user.nip_yayasan, "200001")

    def test_admin_bisa_ubah_nip_yayasan_lewat_edit_user(self):
        target = User.objects.create_user(username="tendiklama", password="testpass123", role="tendik")
        self.client.force_login(self.admin)
        resp = self.client.post(f"/accounts/edit-user/{target.id}/", {
            "first_name": "Tendik", "last_name": "Lama", "email": "", "nidn": "",
            "nip_yayasan": "300002", "role": "tendik", "kode_fakultas": "", "kode_prodi": "",
            "no_hp": "", "status_akun": "aktif", "password_baru": "",
        })
        self.assertEqual(resp.status_code, 302)
        target.refresh_from_db()
        self.assertEqual(target.nip_yayasan, "300002")


class KelolaUserAksesTest(TestCase):
    """Bug fix per 2026-08-03: akses Kelola User dipersempit ke admin +
    operator (fakultas sendiri) saja -- dekan/wadek/kaprodi/sekprodi
    sengaja TIDAK LAGI diikutkan (sebelumnya termasuk lewat
    ROLE_PENGELOLA_SCOPED, dipakai bareng dengan Tinjau Presensi dkk yang
    memang harus tetap terbuka untuk role itu -- Kelola User dipisah jadi
    kebijakannya sendiri)."""

    def setUp(self):
        self.admin = User.objects.create_user(username="kelolaadmin2", password="testpass123", role="admin")
        self.operator = User.objects.create_user(
            username="kelolaoperator", password="testpass123", role="operator", kode_fakultas="FT",
        )
        self.dekan = User.objects.create_user(
            username="kelolaudekan", password="testpass123", role="dekan", kode_fakultas="FT",
        )
        self.kaprodi = User.objects.create_user(
            username="kelolakaprodi", password="testpass123", role="kaprodi", kode_prodi="TI",
        )
        self.dosen_ft = User.objects.create_user(
            username="kelolatarget", password="testpass123", role="dosen", kode_fakultas="FT", kode_prodi="TI",
        )

    def test_dekan_ditolak_kelola_user(self):
        self.client.force_login(self.dekan)
        resp = self.client.get("/accounts/kelola-user/")
        self.assertEqual(resp.status_code, 302)

    def test_kaprodi_ditolak_tambah_user(self):
        self.client.force_login(self.kaprodi)
        resp = self.client.post("/accounts/tambah-user/", {
            "username": "gagaldibuat", "first_name": "Gagal", "last_name": "",
            "email": "", "nidn": "", "nip_yayasan": "", "role": "dosen",
            "kode_fakultas": "", "kode_prodi": "", "no_hp": "", "password": "testpass123",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(User.objects.filter(username="gagaldibuat").exists())

    def test_dekan_ditolak_edit_user(self):
        self.client.force_login(self.dekan)
        resp = self.client.post(f"/accounts/edit-user/{self.dosen_ft.id}/", {
            "first_name": "Diubah", "last_name": "", "email": "", "nidn": "",
            "nip_yayasan": "", "role": "dosen", "kode_fakultas": "FT", "kode_prodi": "TI",
            "no_hp": "", "status_akun": "aktif", "password_baru": "",
        })
        self.assertEqual(resp.status_code, 302)
        self.dosen_ft.refresh_from_db()
        self.assertNotEqual(self.dosen_ft.first_name, "Diubah")

    def test_operator_fakultas_sendiri_diterima(self):
        self.client.force_login(self.operator)
        resp = self.client.get("/accounts/kelola-user/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(self.dosen_ft, resp.context["page_obj"].object_list)

    def test_admin_tetap_diterima(self):
        self.client.force_login(self.admin)
        resp = self.client.get("/accounts/kelola-user/")
        self.assertEqual(resp.status_code, 200)
