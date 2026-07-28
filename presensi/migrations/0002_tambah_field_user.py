"""Tahap 1/3 migrasi kunci identitas: nidn (CharField) -> user (FK ke
accounts.User). Field `user` ditambah NULLABLE dulu di sini supaya baris
yang sudah ada tidak gagal -- diisi lewat migrasi data berikutnya
(0003_backfill_user_dari_nidn), baru DIWAJIBKAN + field nidn lama
dihapus di 0004_finalisasi_kunci_user setelah dipastikan tidak ada baris
yang gagal terisi (lihat instruksi deploy di 0004).
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('presensi', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='jadwalkerja',
            name='user',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name='jadwal_presensi_set', to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='perangkat',
            name='user',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name='perangkat_presensi_set', to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='enrolmentwajah',
            name='user',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name='enrolment_wajah', to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='presensi',
            name='user',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name='presensi_set', to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='izincuti',
            name='user',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name='izin_cuti_set', to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='izincuti',
            name='approver_user',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='izin_cuti_disetujui_set', to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='logkecurangan',
            name='user',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name='log_kecurangan_set', to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
