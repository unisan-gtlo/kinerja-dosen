from django.core.management.base import BaseCommand

from accounts.models import User


class Command(BaseCommand):
    help = (
        'Reset password semua User(role=tendik) supaya SAMA dengan username '
        'masing-masing (mempermudah onboarding -- tendik cukup diberi tahu '
        '"username dan password sama"). Default DRY-RUN (cuma menampilkan '
        'daftar yang akan diubah) -- tambahkan --yes untuk benar-benar '
        'menyimpan perubahan.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes', action='store_true',
            help='Benar-benar simpan perubahan password (tanpa ini, cuma pratinjau/dry-run).',
        )

    def handle(self, *args, **options):
        terapkan = options['yes']
        tendik_users = User.objects.filter(role='tendik').order_by('username')
        total = tendik_users.count()

        if total == 0:
            self.stdout.write(self.style.WARNING('Tidak ada User(role=tendik) ditemukan.'))
            return

        mode = 'MENERAPKAN PERUBAHAN' if terapkan else 'DRY-RUN (belum disimpan, tambahkan --yes untuk menerapkan)'
        self.stdout.write(self.style.MIGRATE_HEADING(f'Reset password tendik — {mode}'))
        self.stdout.write(f'Total user role=tendik: {total}\n')

        diubah = 0
        dilewati = 0
        for user in tendik_users:
            if not user.username:
                self.stdout.write(self.style.ERROR(f'  - id={user.id}: username kosong, dilewati'))
                dilewati += 1
                continue

            self.stdout.write(f'  - {user.username} ({user.get_full_name() or "-"})')
            if terapkan:
                user.set_password(user.username)
                user.save(update_fields=['password'])
            diubah += 1

        self.stdout.write('')
        if terapkan:
            self.stdout.write(self.style.SUCCESS(f'Selesai: {diubah} password diubah, {dilewati} dilewati.'))
        else:
            self.stdout.write(self.style.WARNING(
                f'Dry-run selesai: {diubah} AKAN diubah, {dilewati} dilewati. '
                'Jalankan ulang dengan --yes untuk benar-benar menerapkan.'
            ))
