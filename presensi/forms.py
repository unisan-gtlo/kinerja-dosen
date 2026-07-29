from django import forms

from .models import IzinCuti


class IzinCutiForm(forms.ModelForm):
    """Form pengajuan izin/sakit/cuti/dinas mandiri -- lihat
    presensi/views.py::halaman_izin."""

    class Meta:
        model = IzinCuti
        fields = ["tipe", "tanggal_mulai", "tanggal_selesai", "alasan", "lampiran"]
        widgets = {
            "tipe": forms.RadioSelect,
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
