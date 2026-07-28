"""Tahap 2/3: isi field `user` (ditambah di 0002) dari field `nidn` lama,
dengan mencocokkan ke accounts.User.nidn -- lihat CLAUDE.md untuk alasan
migrasi ini (staf/tendik tidak punya NIDN, jadi presensi tidak bisa terus
dikunci NIDN).

PENTING sebelum lanjut ke 0004_finalisasi_kunci_user (yang akan
MEWAJIBKAN field user + MENGHAPUS field nidn lama): pastikan dulu tidak
ada baris yang gagal dicocokkan. Setelah migrasi ini jalan, jalankan
manage.py migrate cuma sampai sini (`migrate presensi 0003`), lalu cek:

    python manage.py shell -c "
    from presensi.models import Presensi, JadwalKerja, Perangkat, EnrolmentWajah, IzinCuti, LogKecurangan
    for M in [Presensi, Perangkat, EnrolmentWajah, IzinCuti, LogKecurangan]:
        print(M.__name__, M.objects.filter(user__isnull=True).count(), 'baris belum ketemu user')
    print('JadwalKerja tanpa user (wajar, berarti jadwal default lokasi):',
          JadwalKerja.objects.filter(user__isnull=True).count())
    "

Kalau ada baris (selain JadwalKerja) yang masih 0 user setelah ini,
JANGAN lanjut ke 0004 dulu -- perbaiki NIDN-nya di accounts.User dulu
(kemungkinan besar akun itu NIDN-nya salah ketik/kosong), baru migrate
lagi dari 0003 supaya backfill jalan ulang untuk baris yang tersisa.
"""
from django.db import migrations

NAMA_MODEL_BERKUNCI_NIDN = [
    'JadwalKerja', 'Perangkat', 'EnrolmentWajah', 'Presensi', 'IzinCuti', 'LogKecurangan',
]


def backfill_user(apps, schema_editor):
    User = apps.get_model('accounts', 'User')

    for nama_model in NAMA_MODEL_BERKUNCI_NIDN:
        Model = apps.get_model('presensi', nama_model)
        tidak_ketemu = []
        for row in Model.objects.filter(user__isnull=True).exclude(nidn=''):
            user = User.objects.filter(nidn=row.nidn).first()
            if user:
                row.user = user
                row.save(update_fields=['user'])
            else:
                tidak_ketemu.append((row.pk, row.nidn))
        if tidak_ketemu:
            print(
                f"\nPERINGATAN: {len(tidak_ketemu)} baris {nama_model} tidak ketemu "
                f"user yang cocok (NIDN tidak ada di accounts.User): {tidak_ketemu[:10]}"
            )

    # approver (CharField lama "NIDN/ID atasan") -> approver_user (FK), best-effort.
    # Fitur approval izin belum pernah dipakai jadi kemungkinan besar kosong semua.
    IzinCuti = apps.get_model('presensi', 'IzinCuti')
    for row in IzinCuti.objects.exclude(approver='').filter(approver_user__isnull=True):
        user = User.objects.filter(nidn=row.approver).first()
        if user:
            row.approver_user = user
            row.save(update_fields=['approver_user'])


def reverse_backfill(apps, schema_editor):
    for nama_model in NAMA_MODEL_BERKUNCI_NIDN:
        Model = apps.get_model('presensi', nama_model)
        Model.objects.update(user=None)
    IzinCuti = apps.get_model('presensi', 'IzinCuti')
    IzinCuti.objects.update(approver_user=None)


class Migration(migrations.Migration):

    dependencies = [
        ('presensi', '0002_tambah_field_user'),
    ]

    operations = [
        migrations.RunPython(backfill_user, reverse_backfill),
    ]
