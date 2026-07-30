from django import forms

from accounts.models import ROLE_CHOICES
from master.models import Fakultas, Prodi
from .models import HariLibur, IzinCuti, KelompokPresensi, NAMA_BULAN, TargetKerjaBulanan

HARI_CHOICES = [
    (0, "Senin"), (1, "Selasa"), (2, "Rabu"), (3, "Kamis"), (4, "Jumat"), (5, "Sabtu"), (6, "Minggu"),
]
BULAN_CHOICES = list(enumerate(NAMA_BULAN, 1))


class IzinCutiForm(forms.ModelForm):
    """Form pengajuan izin/sakit/cuti/dinas mandiri -- lihat
    presensi/views.py::halaman_izin."""

    # Field dibuat manual (bukan cuma lewat Meta.widgets) supaya TIDAK ada
    # opsi kosong "---------" yang otomatis ditambah Django untuk field
    # wajib tanpa default -- "Izin" jadi pilihan default yang sudah terpilih.
    tipe = forms.ChoiceField(
        choices=IzinCuti.Tipe.choices, widget=forms.RadioSelect, initial=IzinCuti.Tipe.IZIN,
    )

    class Meta:
        model = IzinCuti
        fields = ["tipe", "tanggal_mulai", "tanggal_selesai", "alasan", "lampiran"]
        widgets = {
            "tanggal_mulai": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "tanggal_selesai": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "alasan": forms.Textarea(attrs={
                "class": "form-control", "rows": 3, "placeholder": "Tulis keterangan...",
            }),
            "lampiran": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned = super().clean()
        mulai = cleaned.get("tanggal_mulai")
        selesai = cleaned.get("tanggal_selesai")
        if mulai and selesai and selesai < mulai:
            raise forms.ValidationError("Tanggal selesai tidak boleh sebelum tanggal mulai.")
        return cleaned


class KelompokPresensiForm(forms.ModelForm):
    """Pengaturan kelompok jam kerja -- lihat presensi/views.py::
    pengaturan_kelompok. roles & hari_kerja dibuat manual (checkbox, bukan
    input teks dipisah koma) supaya HR non-teknis lebih mudah pakainya."""
    roles = forms.MultipleChoiceField(
        choices=ROLE_CHOICES, widget=forms.CheckboxSelectMultiple,
        help_text="Role akun yang otomatis masuk kelompok ini.",
    )
    hari_kerja = forms.MultipleChoiceField(
        choices=HARI_CHOICES, widget=forms.CheckboxSelectMultiple,
        help_text="Hari kerja kelompok ini.",
    )

    class Meta:
        model = KelompokPresensi
        fields = ["nama", "roles", "hari_kerja", "jam_masuk", "jam_pulang", "toleransi_menit", "aktif"]
        widgets = {
            "nama": forms.TextInput(attrs={"class": "form-control"}),
            "jam_masuk": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "jam_pulang": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "toleransi_menit": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def clean_hari_kerja(self):
        # ArrayField-nya PositiveSmallIntegerField -- MultipleChoiceField
        # selalu kembalikan list string, perlu dikonversi ke int manual.
        return [int(hari) for hari in self.cleaned_data["hari_kerja"]]


class HariLiburForm(forms.ModelForm):
    """Pengaturan kalender hari libur -- lihat presensi/views.py::
    pengaturan_hari_libur."""

    class Meta:
        model = HariLibur
        fields = ["tanggal", "keterangan", "jenis"]
        widgets = {
            "tanggal": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "keterangan": forms.TextInput(attrs={"class": "form-control"}),
            "jenis": forms.Select(attrs={"class": "form-select"}),
        }


class TargetKerjaBulananForm(forms.ModelForm):
    """Pengaturan target hari & jam kerja bulanan per kelompok -- lihat
    presensi/views.py::pengaturan_target."""
    bulan = forms.ChoiceField(choices=BULAN_CHOICES, widget=forms.Select(attrs={"class": "form-select"}))

    class Meta:
        model = TargetKerjaBulanan
        fields = ["kelompok", "bulan", "tahun", "target_hari_kerja", "target_jam_kerja"]
        widgets = {
            "kelompok": forms.Select(attrs={"class": "form-select"}),
            "tahun": forms.NumberInput(attrs={"class": "form-control"}),
            "target_hari_kerja": forms.NumberInput(attrs={"class": "form-control"}),
            "target_jam_kerja": forms.NumberInput(attrs={"class": "form-control", "step": "0.5"}),
        }


class LaporanSerdosForm(forms.Form):
    """Parameter Laporan Daftar Hadir Dosen Serdos (LLDIKTI) -- lihat
    presensi/views.py::halaman_laporan_serdos. Nama/NIP penandatangan
    diisi otomatis dari data Pejabat Struktural SIMDA kalau ketemu (lihat
    simda_dosen/utils.py::get_pejabat_aktif), tapi tetap bisa diedit
    manual (mis. kalau mau ditandatangani pejabat lain, atau data SIMDA
    belum lengkap)."""
    bulan = forms.ChoiceField(choices=BULAN_CHOICES, widget=forms.Select(attrs={"class": "form-select"}))
    tahun = forms.IntegerField(widget=forms.NumberInput(attrs={"class": "form-control"}))
    kota = forms.CharField(initial="Gorontalo", widget=forms.TextInput(attrs={"class": "form-control"}))
    tanggal_cetak = forms.DateField(widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}))
    jabatan_penandatangan = forms.CharField(
        initial="Rektor", widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    nama_penandatangan = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    nip_penandatangan = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))


KATEGORI_LAPORAN_INTERNAL_CHOICES = [
    ("", "Semua Kategori"), ("dosen", "Dosen"), ("pejabat", "Pejabat"), ("tendik", "Tendik"),
]


class LaporanInternalForm(forms.Form):
    """Filter Laporan Presensi Internal -- lihat presensi/views.py::
    halaman_laporan_internal. Pilihan Fakultas/Prodi diisi dinamis di
    __init__ (query saat request, bukan saat modul di-import) supaya
    daftarnya selalu sesuai data master terbaru."""
    bulan = forms.ChoiceField(choices=BULAN_CHOICES, widget=forms.Select(attrs={"class": "form-select"}))
    tahun = forms.IntegerField(widget=forms.NumberInput(attrs={"class": "form-control"}))
    kategori = forms.ChoiceField(
        choices=KATEGORI_LAPORAN_INTERNAL_CHOICES, required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    fakultas = forms.ChoiceField(required=False, widget=forms.Select(attrs={"class": "form-select"}))
    prodi = forms.ChoiceField(required=False, widget=forms.Select(attrs={"class": "form-select"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fakultas"].choices = [("", "Semua Fakultas")] + [
            (f.kode_fakultas, f"{f.kode_fakultas} - {f.nama_fakultas}") for f in Fakultas.objects.all()
        ]
        self.fields["prodi"].choices = [("", "Semua Prodi")] + [
            (p.kode_prodi, f"{p.kode_prodi} - {p.nama_prodi}") for p in Prodi.objects.all()
        ]
