import io

import openpyxl
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
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


class ImportUserTendikTest(TestCase):
    """Bug fix 2026-08-05: import_user (Kelola User -> Import Excel) punya
    valid_roles yang belum menyertakan 'tendik' -- baris role=tendik selalu
    diturunkan diam-diam jadi 'dosen', dan kolom NIP Yayasan belum pernah
    dibaca sama sekali dari Excel (akun tendik hasil import tidak pernah
    tertaut ke DataTendik SIMDA). Template & parsing-nya sekarang menambah
    kolom ke-11 (NIP Yayasan)."""

    def setUp(self):
        self.admin = User.objects.create_user(username="importuseradmin", password="testpass123", role="admin")

    def _buat_file_excel(self, rows):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["baris header 1 (diabaikan)"])
        ws.append(["baris header 2 (diabaikan)"])
        for row in rows:
            ws.append(row)
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return SimpleUploadedFile(
            "import.xlsx", buffer.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def test_import_role_tendik_dan_nip_yayasan_tersimpan(self):
        file_excel = self._buat_file_excel([[
            "tendikimport1", "", "Budi", "Import", "budi@unichsan.ac.id",
            "081234567890", "tendik", "", "", "rahasia123", "0120990099",
        ]])
        self.client.force_login(self.admin)
        resp = self.client.post("/accounts/import-user/", {"file_excel": file_excel})
        self.assertEqual(resp.status_code, 302)

        user = User.objects.get(username="tendikimport1")
        self.assertEqual(user.role, "tendik")
        self.assertEqual(user.nip_yayasan, "0120990099")


class ResetPasswordTendikCommandTest(TestCase):
    """manage.py reset_password_tendik -- bulk reset password semua
    User(role=tendik) supaya sama dengan username (permintaan admin untuk
    mempermudah onboarding tendik, lihat CLAUDE.md). Default dry-run,
    --yes untuk benar-benar menyimpan; hanya menyasar role=tendik."""

    def setUp(self):
        self.tendik1 = User.objects.create_user(username="0120990001", password="passwordlama1", role="tendik")
        self.tendik2 = User.objects.create_user(username="0120990002", password="passwordlama2", role="tendik")
        self.dosen = User.objects.create_user(username="dosentakikut", password="passwordlamadosen", role="dosen")

    def test_dry_run_tidak_mengubah_password(self):
        call_command("reset_password_tendik", stdout=io.StringIO())
        self.tendik1.refresh_from_db()
        self.assertTrue(self.tendik1.check_password("passwordlama1"))

    def test_yes_mengubah_password_tendik_jadi_sama_dengan_username(self):
        call_command("reset_password_tendik", "--yes", stdout=io.StringIO())
        self.tendik1.refresh_from_db()
        self.tendik2.refresh_from_db()
        self.dosen.refresh_from_db()

        self.assertTrue(self.tendik1.check_password("0120990001"))
        self.assertTrue(self.tendik2.check_password("0120990002"))
        # Role lain (dosen dkk) sama sekali tidak disentuh.
        self.assertTrue(self.dosen.check_password("passwordlamadosen"))
