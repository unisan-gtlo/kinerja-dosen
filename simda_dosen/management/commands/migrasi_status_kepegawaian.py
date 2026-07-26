from django.core.management.base import BaseCommand

from accounts.models import User
from simda_dosen.models import DataDosen, StatusKepegawaianPublik


# Pemetaan nilai lama (accounts.User.status_kepegawaian) ke kode baru
# (kepegawaian_ref.StatusKepegawaian di SIMDA) -- dikonfirmasi user saat
# migrasi field ini ke SIMDA (2026-07-26).
MAPPING = {
    'Aktif': 'AKTIF',
    'Tugas Belajar': 'TUGAS_BELAJAR',
    'Lanjut Studi': 'IZIN_BELAJAR',
    'Keluar': 'MUTASI',
    'Meninggal': 'WAFAT',
}


class Command(BaseCommand):
    help = (
        'Migrasi satu-kali nilai lama User.status_kepegawaian (SIKD lokal) ke '
        'DataDosen.status_kepegawaian_id (SIMDA), per dosen dicocokkan lewat nidn. '
        'Jalankan SEKALI setelah migration+seed kepegawaian_ref SIMDA & view publik '
        'sudah di-apply, SEBELUM field User.status_kepegawaian dihapus. '
        'Pakai --dry-run dulu untuk lihat preview tanpa menulis apa pun.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                             help='Tampilkan rencana perubahan tanpa menyimpan.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        kode_ke_id = {
            s.kode: s.id
            for s in StatusKepegawaianPublik.objects.using('simda').all()
        }
        hilang = [kode for kode in MAPPING.values() if kode not in kode_ke_id]
        if hilang:
            self.stdout.write(self.style.ERROR(
                f'Kode StatusKepegawaian berikut belum ada di view SIMDA: {hilang}. '
                'Pastikan migration 0002 (seed) & buat_view_kepegawaian_publik.sql '
                'sudah dijalankan di SIMDA sebelum lanjut.'
            ))
            return

        dosen_users = User.objects.filter(
            role='dosen', status_kepegawaian__isnull=False
        ).exclude(status_kepegawaian='').order_by('username')

        total = dosen_users.count()
        berhasil = 0
        dilewati = []

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'{"[DRY RUN] " if dry_run else ""}Migrasi status_kepegawaian — {total} user role=dosen berstatus terisi'
        ))

        for user in dosen_users:
            nilai_lama = user.status_kepegawaian
            kode_baru = MAPPING.get(nilai_lama)
            if not kode_baru:
                dilewati.append((user, f'nilai lama tidak dikenal: "{nilai_lama}"'))
                continue

            nidn = (user.nidn or '').strip()
            if not nidn:
                dilewati.append((user, 'nidn kosong'))
                continue

            profil = DataDosen.objects.using('simda').filter(nidn=nidn).first()
            if not profil:
                dilewati.append((user, f'nidn "{nidn}" tidak cocok ke DataDosen SIMDA'))
                continue

            status_id = kode_ke_id[kode_baru]
            self.stdout.write(
                f'  {user.username} ({user.get_full_name()}): '
                f'"{nilai_lama}" -> {kode_baru} (id={status_id})'
                + (' [sudah sama]' if profil.status_kepegawaian_id == status_id else '')
            )
            if not dry_run and profil.status_kepegawaian_id != status_id:
                profil.status_kepegawaian_id = status_id
                profil.save(update_fields=['status_kepegawaian_id'])
            berhasil += 1

        self.stdout.write(self.style.SUCCESS(f'\nBerhasil dipetakan: {berhasil}/{total}'))
        if dilewati:
            self.stdout.write(self.style.WARNING(f'Dilewati: {len(dilewati)}'))
            for user, alasan in dilewati:
                self.stdout.write(f'  - {user.username} ({user.get_full_name()}): {alasan}')

        if dry_run:
            self.stdout.write(self.style.WARNING(
                '\nIni baru DRY RUN -- tidak ada perubahan tersimpan. '
                'Jalankan ulang tanpa --dry-run kalau hasil di atas sudah sesuai.'
            ))
