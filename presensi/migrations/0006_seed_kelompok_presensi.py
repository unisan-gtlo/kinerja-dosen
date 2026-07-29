"""
Data awal (seed) KelompokPresensi -- dua kelompok yang sudah dikonfirmasi
langsung ke user: Dosen (08.00-14.00) dan Pejabat (08.00-16.00), sama-sama
Senin-Sabtu. Dibuat lewat migrasi supaya langsung tersedia begitu fitur ini
di-deploy, tidak perlu input manual lewat admin dulu.
"""
from datetime import time

from django.db import migrations


ROLES_PEJABAT = ["dekan", "wadek", "kaprodi", "sekprodi", "rektorat", "biro"]


def buat_kelompok_default(apps, schema_editor):
    KelompokPresensi = apps.get_model("presensi", "KelompokPresensi")

    if not KelompokPresensi.objects.filter(nama="Dosen").exists():
        KelompokPresensi.objects.create(
            nama="Dosen",
            roles=["dosen"],
            hari_kerja=[0, 1, 2, 3, 4, 5],
            jam_masuk=time(8, 0),
            jam_pulang=time(14, 0),
            toleransi_menit=15,
            aktif=True,
        )

    if not KelompokPresensi.objects.filter(nama="Pejabat").exists():
        KelompokPresensi.objects.create(
            nama="Pejabat",
            roles=ROLES_PEJABAT,
            hari_kerja=[0, 1, 2, 3, 4, 5],
            jam_masuk=time(8, 0),
            jam_pulang=time(16, 0),
            toleransi_menit=15,
            aktif=True,
        )


def hapus_kelompok_default(apps, schema_editor):
    KelompokPresensi = apps.get_model("presensi", "KelompokPresensi")
    KelompokPresensi.objects.filter(nama__in=["Dosen", "Pejabat"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("presensi", "0005_harilibur_kelompokpresensi_presensi_kelompok"),
    ]

    operations = [
        migrations.RunPython(buat_kelompok_default, hapus_kelompok_default),
    ]
