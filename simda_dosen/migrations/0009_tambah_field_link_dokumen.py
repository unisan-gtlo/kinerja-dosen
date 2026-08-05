# Ditulis manual (bukan hasil makemigrations) -- autodetector Django
# tidak melacak perubahan field pada model managed=False yang sudah ada
# sebelumnya (dicek lewat --dry-run: "No changes detected"). Ini murni
# state bookkeeping Django, TIDAK ada SQL nyata yang dieksekusi untuk
# model unmanaged -- kolom fisiknya harus ditambahkan manual di SIMDA
# lewat tambah_kolom_link_dokumen.sql (repo simda terpisah).
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('simda_dosen', '0008_riwayatpelatihantendik_riwayatpendidikantendik_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='datadosen',
            name='link_ktp',
            field=models.URLField(blank=True, verbose_name='Link KTP (alternatif)'),
        ),
        migrations.AddField(
            model_name='datadosen',
            name='link_npwp',
            field=models.URLField(blank=True, verbose_name='Link NPWP (alternatif)'),
        ),
        migrations.AddField(
            model_name='datadosen',
            name='link_sk_pengangkatan',
            field=models.URLField(blank=True, verbose_name='Link SK Pengangkatan (alternatif)'),
        ),
        migrations.AddField(
            model_name='riwayatpendidikantendik',
            name='link_ijazah',
            field=models.URLField(blank=True, verbose_name='Link Ijazah (alternatif)'),
        ),
        migrations.AddField(
            model_name='riwayatpelatihantendik',
            name='link_sertifikat',
            field=models.URLField(blank=True, verbose_name='Link Sertifikat (alternatif)'),
        ),
        migrations.AddField(
            model_name='riwayatprestasitendik',
            name='link_bukti',
            field=models.URLField(blank=True, verbose_name='Link Bukti (alternatif)'),
        ),
    ]
