from django.core.management.base import BaseCommand
from django.db.models import Q

from accounts.models import User


class Command(BaseCommand):
    help = (
        'Isi nip_yayasan yang masih kosong untuk semua User(role=tendik) '
        'dengan nilai username masing-masing (akun-akun ini dibuat sebelum '
        'kolom NIP Yayasan ditambahkan ke form Import Excel Kelola User, '
        'usernamenya sudah berupa angka NIP Yayasan). Default DRY-RUN -- '
        'tambahkan --yes untuk benar-benar menyimpan perubahan.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes', action='store_true',
            help='Benar-benar simpan perubahan nip_yayasan (tanpa ini, cuma pratinjau/dry-run).',
        )

    def handle(self, *args, **options):
        terapkan = options['yes']
        tendik_kosong = User.objects.filter(
            Q(nip_yayasan__isnull=True) | Q(nip_yayasan=''), role='tendik',
        ).order_by('username')
        total = tendik_kosong.count()

        if total == 0:
            self.stdout.write(self.style.SUCCESS('Tidak ada User(role=tendik) dengan nip_yayasan kosong.'))
            return

        mode = 'MENERAPKAN PERUBAHAN' if terapkan else 'DRY-RUN (belum disimpan, tambahkan --yes untuk menerapkan)'
        self.stdout.write(self.style.MIGRATE_HEADING(f'Backfill nip_yayasan tendik — {mode}'))
        self.stdout.write(f'Total user role=tendik dengan nip_yayasan kosong: {total}\n')

        diisi = 0
        for user in tendik_kosong:
            self.stdout.write(f'  - {user.username} ({user.get_full_name() or "-"}) -> nip_yayasan="{user.username}"')
            if terapkan:
                user.nip_yayasan = user.username
                user.save(update_fields=['nip_yayasan'])
            diisi += 1

        self.stdout.write('')
        if terapkan:
            self.stdout.write(self.style.SUCCESS(f'Selesai: {diisi} nip_yayasan diisi.'))
        else:
            self.stdout.write(self.style.WARNING(
                f'Dry-run selesai: {diisi} AKAN diisi. Jalankan ulang dengan --yes untuk benar-benar menerapkan.'
            ))
