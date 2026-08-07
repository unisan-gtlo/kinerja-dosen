"""
Data migration: tandai kelompok "Pejabat" (seed 0006) supaya otomatis
berlaku untuk dosen/tendik yang tercatat AKTIF menjabat struktural di
SIMDA (Kelola Jabatan Struktural, fitur baru), TANPA perlu role akun
login-nya diubah -- lihat presensi.decision.resolve_kelompok dan
simda_dosen.utils.punya_jabatan_struktural_aktif.

Kalau kelompok "Pejabat" sudah pernah dihapus/di-rename manual oleh admin
lewat Pengaturan Presensi, migrasi ini no-op (tidak ada yang di-flag) --
admin bisa mencentang kelompok yang sesuai manual lewat UI Pengaturan
Presensi kapan saja, ini cuma default awal supaya langsung aktif begitu
fitur di-deploy.
"""
from django.db import migrations


def flag_kelompok_pejabat(apps, schema_editor):
    KelompokPresensi = apps.get_model("presensi", "KelompokPresensi")
    KelompokPresensi.objects.filter(nama="Pejabat").update(
        otomatis_dari_jabatan_struktural=True
    )


def unflag_kelompok_pejabat(apps, schema_editor):
    KelompokPresensi = apps.get_model("presensi", "KelompokPresensi")
    KelompokPresensi.objects.filter(nama="Pejabat").update(
        otomatis_dari_jabatan_struktural=False
    )


class Migration(migrations.Migration):

    dependencies = [
        ("presensi", "0012_kelompokpresensi_otomatis_dari_jabatan_struktural"),
    ]

    operations = [
        migrations.RunPython(flag_kelompok_pejabat, unflag_kelompok_pejabat),
    ]
