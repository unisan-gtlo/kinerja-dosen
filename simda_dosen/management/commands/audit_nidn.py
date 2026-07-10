from django.core.management.base import BaseCommand

from accounts.models import User
from simda_dosen.models import DataDosen


class Command(BaseCommand):
    help = (
        'Audit nidn semua User(role=dosen) di SIKD terhadap DataDosen SIMDA. '
        'Jalankan sebelum mengaktifkan CRUD profil/jabfung/pendidikan/BKD yang '
        'langsung menulis ke SIMDA (Fase 2), karena nidn adalah kunci join-nya.'
    )

    def handle(self, *args, **options):
        dosen_users = User.objects.filter(role='dosen').order_by('username')
        total = dosen_users.count()
        kosong = []
        tidak_cocok = []
        cocok = 0

        simda_nidn_set = set(
            DataDosen.objects.using('simda').values_list('nidn', flat=True)
        )

        for user in dosen_users:
            nidn = (user.nidn or '').strip()
            if not nidn:
                kosong.append(user)
            elif nidn not in simda_nidn_set:
                tidak_cocok.append((user, nidn))
            else:
                cocok += 1

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'Audit NIDN — {total} user role=dosen di SIKD'
        ))
        self.stdout.write(self.style.SUCCESS(f'Cocok ke SIMDA : {cocok}'))

        self.stdout.write(self.style.WARNING(f'NIDN kosong    : {len(kosong)}'))
        for user in kosong:
            self.stdout.write(f'  - {user.username} ({user.get_full_name()})')

        self.stdout.write(self.style.ERROR(f'NIDN tidak cocok: {len(tidak_cocok)}'))
        for user, nidn in tidak_cocok:
            self.stdout.write(f'  - {user.username} ({user.get_full_name()}) — nidn="{nidn}" tidak ada di SIMDA')

        if kosong or tidak_cocok:
            self.stdout.write(self.style.WARNING(
                '\nBenerin dulu user di atas (lewat Kelola User SIKD atau admin) '
                'sebelum Fase 2 (CRUD langsung ke SIMDA) diaktifkan untuk mereka — '
                'kalau tidak, get_simda_dosen() akan 404 untuk user tersebut.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('\nSemua user dosen sudah match ke SIMDA. Aman lanjut Fase 2.'))
