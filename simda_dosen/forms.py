from django.db import DatabaseError
from django import forms

from .models import (
    AgamaPublik, DataTendik, GolonganPublik, JenisKepegawaianPublik, StatusKepegawaianPublik, UnitKerja,
    RiwayatPendidikanTendik, RiwayatPelatihanTendik, RiwayatPrestasiTendik,
)


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
    # empty_value=None WAJIB di semua TypedChoiceField ini -- default
    # bawaan Django (`empty_value=''`) bikin _coerce() mengembalikan
    # string kosong saat field dikosongkan, padahal field model-nya
    # IntegerField(null=True) -- akibatnya ValueError saat disimpan
    # ("invalid literal for int() with base 10: ''"), lihat bug fix
    # ProfilSayaTendikForm.agama_id di bawah untuk kejadian nyatanya.
    unit_kerja_id = forms.TypedChoiceField(
        coerce=int, required=False, empty_value=None,
        label="Unit Kerja", widget=forms.Select(attrs={"class": "form-select"}),
    )
    unit_kerja_baru = forms.CharField(
        required=False, label="Atau Ketik Unit Kerja Baru",
        widget=forms.TextInput(attrs={
            "class": "form-control", "placeholder": "Isi kalau unit kerjanya belum ada di dropdown",
        }),
        help_text="Kalau diisi, dipakai (bukan pilihan dropdown di atas) -- otomatis tersimpan sebagai opsi baru.",
    )
    jenis_kepegawaian_id = forms.TypedChoiceField(
        coerce=int, required=False, empty_value=None,
        label="Jenis Kepegawaian", widget=forms.Select(attrs={"class": "form-select"}),
    )
    status_kepegawaian_id = forms.TypedChoiceField(
        coerce=int, required=False, empty_value=None,
        label="Status Kepegawaian", widget=forms.Select(attrs={"class": "form-select"}),
    )
    golongan_id = forms.TypedChoiceField(
        coerce=int, required=False, empty_value=None,
        label="Golongan", widget=forms.Select(attrs={"class": "form-select"}),
    )
    agama_id = forms.TypedChoiceField(
        coerce=int, required=False, empty_value=None,
        label="Agama", widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        # Semua widget DateInput di bawah WAJIB `format="%Y-%m-%d"` --
        # locale id-id (LANGUAGE_CODE) merender tanggal existing sebagai
        # "25-12-1985" secara default (format lokal pertama di locale
        # module), yang TIDAK valid untuk value <input type="date">
        # HTML5 (harus persis ISO 8601) -- browser jadi menampilkan
        # field-nya KOSONG saat form dibuka utk edit walau datanya
        # tersimpan benar, dan kalau form itu di-submit ulang tanpa
        # tanggal disentuh, nilai kosong itu MENIMPA tanggal yang sudah
        # benar jadi NULL. `settings.DATE_INPUT_FORMATS` TIDAK bisa
        # dipakai untuk memperbaiki ini (locale module id-id selalu
        # menang atas setting global selama l10n aktif) -- harus
        # override `format=` per widget.
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
            "tgl_lahir": forms.DateInput(attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"),
            "pendidikan_terakhir": forms.Select(attrs={"class": "form-select"}),
            "no_hp": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "jabatan": forms.TextInput(attrs={"class": "form-control", "placeholder": "mis. Staf Tata Usaha"}),
            "tgl_mulai_kerja": forms.DateInput(attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"),
            "nama_bank": forms.TextInput(attrs={"class": "form-control"}),
            "no_rekening": forms.TextInput(attrs={"class": "form-control"}),
            "atas_nama_rekening": forms.TextInput(attrs={"class": "form-control"}),
            "foto": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "status_pernikahan": forms.TextInput(attrs={"class": "form-control", "placeholder": "mis. Menikah"}),
            "alamat_domisili": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "kode_pos": forms.TextInput(attrs={"class": "form-control"}),
            "bidang_keahlian": forms.TextInput(attrs={"class": "form-control"}),
            "no_sk_pengangkatan": forms.TextInput(attrs={"class": "form-control"}),
            "tgl_sk_pengangkatan": forms.DateInput(attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"),
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


class RiwayatPendidikanTendikForm(forms.ModelForm):
    """Tambah/ubah Riwayat Pendidikan Tendik -- bagian dari halaman
    Profil Tendik (simda_dosen/views.py::tambah_riwayat_pendidikan_tendik).
    `tendik` di-set di view (bukan lewat form), tidak dimasukkan ke
    Meta.fields."""

    class Meta:
        model = RiwayatPendidikanTendik
        fields = [
            "jenjang", "institusi", "jurusan", "tahun_masuk", "tahun_lulus",
            "no_ijazah", "file_ijazah", "link_ijazah", "keterangan",
        ]
        widgets = {
            "jenjang": forms.Select(attrs={"class": "form-select"}),
            "institusi": forms.TextInput(attrs={"class": "form-control"}),
            "jurusan": forms.TextInput(attrs={"class": "form-control"}),
            "tahun_masuk": forms.NumberInput(attrs={"class": "form-control"}),
            "tahun_lulus": forms.NumberInput(attrs={"class": "form-control"}),
            "no_ijazah": forms.TextInput(attrs={"class": "form-control"}),
            "file_ijazah": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "link_ijazah": forms.URLInput(attrs={"class": "form-control", "placeholder": "Atau link Google Drive..."}),
            "keterangan": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class RiwayatPelatihanTendikForm(forms.ModelForm):
    """Tambah/ubah Riwayat Pelatihan Tendik -- bagian dari halaman
    Profil Tendik."""

    class Meta:
        model = RiwayatPelatihanTendik
        fields = [
            "nama_pelatihan", "penyelenggara", "tingkat", "jumlah_jam", "no_sertifikat",
            "tanggal_mulai", "tanggal_selesai", "file_sertifikat", "link_sertifikat", "keterangan",
        ]
        widgets = {
            "nama_pelatihan": forms.TextInput(attrs={"class": "form-control"}),
            "penyelenggara": forms.TextInput(attrs={"class": "form-control"}),
            "tingkat": forms.Select(attrs={"class": "form-select"}),
            "jumlah_jam": forms.NumberInput(attrs={"class": "form-control"}),
            "no_sertifikat": forms.TextInput(attrs={"class": "form-control"}),
            "tanggal_mulai": forms.DateInput(attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"),
            "tanggal_selesai": forms.DateInput(attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"),
            "file_sertifikat": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "link_sertifikat": forms.URLInput(attrs={"class": "form-control", "placeholder": "Atau link Google Drive..."}),
            "keterangan": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class RiwayatPrestasiTendikForm(forms.ModelForm):
    """Tambah/ubah Riwayat Prestasi Tendik -- bagian dari halaman
    Profil Tendik."""

    class Meta:
        model = RiwayatPrestasiTendik
        fields = [
            "nama_prestasi", "pemberi_penghargaan", "tingkat", "tahun",
            "no_sertifikat", "file_bukti", "link_bukti", "keterangan",
        ]
        widgets = {
            "nama_prestasi": forms.TextInput(attrs={"class": "form-control"}),
            "pemberi_penghargaan": forms.TextInput(attrs={"class": "form-control"}),
            "tingkat": forms.Select(attrs={"class": "form-select"}),
            "tahun": forms.NumberInput(attrs={"class": "form-control"}),
            "no_sertifikat": forms.TextInput(attrs={"class": "form-control"}),
            "file_bukti": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "link_bukti": forms.URLInput(attrs={"class": "form-control", "placeholder": "Atau link Google Drive..."}),
            "keterangan": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class ProfilSayaTendikForm(forms.ModelForm):
    """Ubah data pokok Tendik oleh diri sendiri -- halaman "Riwayat Saya"
    (2026-08-04). Meta.fields SENGAJA persis sama dengan
    DataTendik.SELF_SERVICE_FIELDS -- ModelForm tidak bisa menyentuh
    field di luar daftar ini, jadi field kepegawaian/struktural/bank
    (admin-only) otomatis aman terlepas dari apa yang dikirim di POST."""

    # empty_value=None -- lihat catatan bug fix di DataTendikForm di atas
    # (field model agama_id IntegerField(null=True), default empty_value=''
    # bawaan TypedChoiceField bikin ValueError saat disimpan kosong).
    agama_id = forms.TypedChoiceField(
        coerce=int, required=False, empty_value=None,
        label="Agama", widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = DataTendik
        fields = DataTendik.SELF_SERVICE_FIELDS
        widgets = {
            "nik": forms.TextInput(attrs={"class": "form-control"}),
            "nama_lengkap": forms.TextInput(attrs={"class": "form-control"}),
            "jenis_kelamin": forms.Select(attrs={"class": "form-select"}),
            "tempat_lahir": forms.TextInput(attrs={"class": "form-control"}),
            # format="%Y-%m-%d" wajib -- lihat catatan bug fix di Meta DataTendikForm di atas.
            "tgl_lahir": forms.DateInput(attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"),
            "no_hp": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "status_pernikahan": forms.TextInput(attrs={"class": "form-control", "placeholder": "mis. Menikah"}),
            "alamat_domisili": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "kode_pos": forms.TextInput(attrs={"class": "form-control"}),
            "bidang_keahlian": forms.TextInput(attrs={"class": "form-control"}),
            "foto": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "npwp": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        kosong = [("", "---------")]
        try:
            self.fields["agama_id"].choices = kosong + [
                (a.id, a.nama) for a in AgamaPublik.objects.using("simda").order_by("urutan")
            ]
        except DatabaseError:
            self.fields["agama_id"].choices = kosong
