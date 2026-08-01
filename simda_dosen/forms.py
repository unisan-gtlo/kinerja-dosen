from django.db import DatabaseError
from django import forms

from .models import AgamaPublik, DataTendik, GolonganPublik, JenisKepegawaianPublik, StatusKepegawaianPublik, UnitKerja


class DataTendikForm(forms.ModelForm):
    """Form Kelola Data Tendik -- CRUD penuh ke master.data_tendik SIMDA
    (lihat simda_dosen/views.py::tambah_tendik/ubah_tendik). Cakupan
    field SENGAJA selengkap tabel SIMDA aslinya (termasuk NIK/rekening/
    NPWP/foto), permintaan eksplisit user per fitur "Kelola Data Tendik"
    2026-08-01 -- provinsi/kabupaten_domisili_id TIDAK diberi dropdown di
    sini (sama seperti gap yang sudah ada di form Profil Dosen), lihat
    catatan lengkap di DataTendik.__doc__.

    unit_kerja_id/jenis_kepegawaian_id/status_kepegawaian_id/golongan_id/
    agama_id BUKAN FK Django asli (field mentah, lintas-database) --
    di-render manual sebagai dropdown, pilihannya diisi di __init__ dari
    model Publik/mirror terkait (query saat request, bukan saat modul
    di-import, supaya daftarnya selalu sesuai data SIMDA terbaru).
    Dibungkus try/except DatabaseError supaya form tetap bisa dibuka
    (dropdown kosong) kalau akses ke salah satu tabel referensi belum
    lengkap, bukan 500 total -- pola sama dengan get_pejabat_aktif."""
    unit_kerja_id = forms.TypedChoiceField(
        coerce=int, required=False, label="Unit Kerja", widget=forms.Select(attrs={"class": "form-select"}),
    )
    jenis_kepegawaian_id = forms.TypedChoiceField(
        coerce=int, required=False, label="Jenis Kepegawaian", widget=forms.Select(attrs={"class": "form-select"}),
    )
    status_kepegawaian_id = forms.TypedChoiceField(
        coerce=int, required=False, label="Status Kepegawaian", widget=forms.Select(attrs={"class": "form-select"}),
    )
    golongan_id = forms.TypedChoiceField(
        coerce=int, required=False, label="Golongan", widget=forms.Select(attrs={"class": "form-select"}),
    )
    agama_id = forms.TypedChoiceField(
        coerce=int, required=False, label="Agama", widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = DataTendik
        fields = [
            "nip", "nip_yayasan", "nik", "nama_lengkap", "jenis_kelamin", "tempat_lahir", "tgl_lahir",
            "pendidikan_terakhir", "no_hp", "email", "unit_kerja_id", "jabatan", "jenis_kepegawaian_id",
            "status_kepegawaian_id", "golongan_id", "tgl_mulai_kerja", "nama_bank", "no_rekening",
            "atas_nama_rekening", "foto", "is_active", "agama_id", "status_pernikahan", "alamat_domisili",
            "kode_pos", "bidang_keahlian", "no_sk_pengangkatan", "tgl_sk_pengangkatan", "npwp",
        ]
        widgets = {
            "nip": forms.TextInput(attrs={"class": "form-control"}),
            "nip_yayasan": forms.TextInput(attrs={"class": "form-control"}),
            "nik": forms.TextInput(attrs={"class": "form-control"}),
            "nama_lengkap": forms.TextInput(attrs={"class": "form-control"}),
            "jenis_kelamin": forms.Select(attrs={"class": "form-select"}),
            "tempat_lahir": forms.TextInput(attrs={"class": "form-control"}),
            "tgl_lahir": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "pendidikan_terakhir": forms.Select(attrs={"class": "form-select"}),
            "no_hp": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "jabatan": forms.TextInput(attrs={"class": "form-control", "placeholder": "mis. Staf Tata Usaha"}),
            "tgl_mulai_kerja": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "nama_bank": forms.TextInput(attrs={"class": "form-control"}),
            "no_rekening": forms.TextInput(attrs={"class": "form-control"}),
            "atas_nama_rekening": forms.TextInput(attrs={"class": "form-control"}),
            "foto": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "status_pernikahan": forms.TextInput(attrs={"class": "form-control", "placeholder": "mis. Menikah"}),
            "alamat_domisili": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "kode_pos": forms.TextInput(attrs={"class": "form-control"}),
            "bidang_keahlian": forms.TextInput(attrs={"class": "form-control"}),
            "no_sk_pengangkatan": forms.TextInput(attrs={"class": "form-control"}),
            "tgl_sk_pengangkatan": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "npwp": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        kosong = [("", "---------")]
        try:
            self.fields["unit_kerja_id"].choices = kosong + [
                (u.id, str(u)) for u in UnitKerja.objects.using("simda").filter(status=True).order_by("nama")
            ]
            self.fields["jenis_kepegawaian_id"].choices = kosong + [
                (j.id, j.nama) for j in JenisKepegawaianPublik.objects.using("simda").all()
            ]
            self.fields["status_kepegawaian_id"].choices = kosong + [
                (s.id, s.nama) for s in StatusKepegawaianPublik.objects.using("simda").all()
            ]
            self.fields["golongan_id"].choices = kosong + [
                (g.id, f"{g.kode} ({g.pangkat})") for g in GolonganPublik.objects.using("simda").all()
            ]
            self.fields["agama_id"].choices = kosong + [
                (a.id, a.nama) for a in AgamaPublik.objects.using("simda").order_by("urutan")
            ]
        except DatabaseError:
            for nama_field in (
                "unit_kerja_id", "jenis_kepegawaian_id", "status_kepegawaian_id", "golongan_id", "agama_id",
            ):
                self.fields[nama_field].choices = kosong
