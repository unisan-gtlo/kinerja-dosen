from django.shortcuts import get_object_or_404

from .models import DataDosen


def get_simda_dosen(user):
    """Ambil baris DataDosen SIMDA milik `user` SIKD, di-join lewat nidn.
    404 kalau user.nidn kosong atau tidak match ke SIMDA -- jalankan
    `python manage.py audit_nidn` untuk cek/benerin data sebelum ini dipakai.
    """
    if not user.nidn:
        raise DataDosen.DoesNotExist(f'User {user.username} belum punya nidn di SIKD')
    return get_object_or_404(DataDosen, nidn=user.nidn)
