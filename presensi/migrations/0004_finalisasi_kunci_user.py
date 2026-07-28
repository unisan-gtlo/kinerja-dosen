"""Tahap 3/3: wajibkan field `user` (sekarang seharusnya sudah terisi
semua lewat 0003) dan hapus field `nidn`/`approver` (CharField) lama.

JANGAN jalankan migrasi ini sebelum memverifikasi hasil 0003 (lihat
docstring di situ) -- kalau masih ada baris yang user-nya kosong (selain
JadwalKerja, yang memang boleh kosong untuk jadwal default lokasi),
ALTER COLUMN ... SET NOT NULL di migrasi ini akan GAGAL (aman -- migrasi
akan berhenti & rollback, bukan korupsi data -- tapi tetap perbaiki dulu
NIDN yang tidak cocok, baru migrate lagi).
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('presensi', '0003_backfill_user_dari_nidn'),
    ]

    operations = [
        # --- Presensi ---
        migrations.AlterUniqueTogether(
            name='presensi',
            unique_together={('user', 'tanggal')},
        ),
        migrations.RemoveField(model_name='presensi', name='nidn'),
        migrations.AlterField(
            model_name='presensi',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='presensi_set', to=settings.AUTH_USER_MODEL,
            ),
        ),

        # --- Perangkat ---
        migrations.AlterUniqueTogether(
            name='perangkat',
            unique_together={('user', 'device_id')},
        ),
        migrations.RemoveField(model_name='perangkat', name='nidn'),
        migrations.AlterField(
            model_name='perangkat',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='perangkat_presensi_set', to=settings.AUTH_USER_MODEL,
            ),
        ),

        # --- EnrolmentWajah ---
        migrations.RemoveField(model_name='enrolmentwajah', name='nidn'),
        migrations.AlterField(
            model_name='enrolmentwajah',
            name='user',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='enrolment_wajah', to=settings.AUTH_USER_MODEL,
            ),
        ),

        # --- JadwalKerja (user TETAP boleh kosong -- berarti jadwal default lokasi) ---
        migrations.RemoveField(model_name='jadwalkerja', name='nidn'),

        # --- IzinCuti ---
        migrations.RemoveField(model_name='izincuti', name='nidn'),
        migrations.RemoveField(model_name='izincuti', name='approver'),
        migrations.RenameField(model_name='izincuti', old_name='approver_user', new_name='approver'),
        migrations.AlterField(
            model_name='izincuti',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='izin_cuti_set', to=settings.AUTH_USER_MODEL,
            ),
        ),

        # --- LogKecurangan ---
        migrations.RemoveField(model_name='logkecurangan', name='nidn'),
        migrations.AlterField(
            model_name='logkecurangan',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='log_kecurangan_set', to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
