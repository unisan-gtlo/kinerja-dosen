"""
Data awal (seed) kelompok "Staf/Tendik" -- jam kerja sama persis dengan
"Pejabat" (08.00-16.00, Senin-Sabtu), tapi baris kelompok terpisah supaya
ke depannya jam/target bulanan tendik bisa diatur beda dari pejabat tanpa
perlu migrasi skema lagi (lihat CLAUDE.md § 9 & diskusi dengan user).
"""
from datetime import time

from django.db import migrations


def buat_kelompok_staf_tendik(apps, schema_editor):
    KelompokPresensi = apps.get_model("presensi", "KelompokPresensi")

    if not KelompokPresensi.objects.filter(nama="Staf/Tendik").exists():
        KelompokPresensi.objects.create(
            nama="Staf/Tendik",
            roles=["tendik"],
            hari_kerja=[0, 1, 2, 3, 4, 5],
            jam_masuk=time(8, 0),
            jam_pulang=time(16, 0),
            toleransi_menit=15,
            aktif=True,
        )


def hapus_kelompok_staf_tendik(apps, schema_editor):
    KelompokPresensi = apps.get_model("presensi", "KelompokPresensi")
    KelompokPresensi.objects.filter(nama="Staf/Tendik").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("presensi", "0007_targetkerjabulanan"),
    ]

    operations = [
        migrations.RunPython(buat_kelompok_staf_tendik, hapus_kelompok_staf_tendik),
    ]
