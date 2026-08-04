from django.template import Context, Template
from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User
from .models import Pengaturan


class FormatLinkFilterTest(TestCase):
    """master_extras::format_link -- template URL profil riset (SINTA/
    Scopus/dst, disimpan di Pengaturan) diatur admin, bukan hardcode di
    template, supaya kalau domain/format URL berubah cukup diedit di
    halaman Pengaturan (bug awal: URL SINTA hardcode "/profile/{id}"
    yang sudah tidak berfungsi, seharusnya "/authors/profile/{id}/
    ?view=garuda")."""

    def _render(self, tpl, idval):
        t = Template("{% load master_extras %}{{ tpl|format_link:idval }}")
        return t.render(Context({"tpl": tpl, "idval": idval}))

    def test_placeholder_id_diganti_nilai_asli(self):
        hasil = self._render(
            "https://sinta.kemdiktisaintek.go.id/authors/profile/{id}/?view=garuda", "6172523",
        )
        self.assertEqual(hasil, "https://sinta.kemdiktisaintek.go.id/authors/profile/6172523/?view=garuda")

    def test_id_kosong_hasil_kosong(self):
        self.assertEqual(self._render("https://x/{id}", ""), "")

    def test_template_kosong_hasil_kosong(self):
        self.assertEqual(self._render("", "123"), "")


class SimpanPengaturanUrlTemplateTest(TestCase):
    """simpan_pengaturan -- template URL SINTA/Scopus/dst bisa diubah
    admin tanpa perlu edit kode. Field yang dikirim kosong TIDAK
    menghapus nilai lama (supaya link tidak mendadak rusak
    institusi-wide gara-gara submit form yang salah)."""

    def setUp(self):
        self.admin = User.objects.create_user(username="masteradmin", password="testpass123", role="admin")
        self.client = Client()
        self.client.login(username="masteradmin", password="testpass123")

    def test_admin_bisa_ubah_template_sinta(self):
        self.client.post(reverse("master:simpan_pengaturan"), {
            "status_input": "buka",
            "url_template_sinta": "https://sinta.kemdiktisaintek.go.id/authors/profile/{id}/?view=garuda",
        })
        pengaturan = Pengaturan.objects.first()
        self.assertEqual(
            pengaturan.url_template_sinta,
            "https://sinta.kemdiktisaintek.go.id/authors/profile/{id}/?view=garuda",
        )

    def test_submit_kosong_tidak_menghapus_nilai_lama(self):
        Pengaturan.objects.create(url_template_scopus="https://contoh-lama/{id}")
        self.client.post(reverse("master:simpan_pengaturan"), {
            "status_input": "buka",
            "url_template_scopus": "",
        })
        pengaturan = Pengaturan.objects.first()
        self.assertEqual(pengaturan.url_template_scopus, "https://contoh-lama/{id}")
