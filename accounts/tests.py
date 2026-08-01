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
