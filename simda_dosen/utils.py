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


def get_simda_dosen_or_none(user):
    """Sama seperti get_simda_dosen, tapi return None (bukan 404) kalau tidak
    ketemu -- dipakai di dashboard/laporan yang harus tetap render walau ada
    user yang nidn-nya belum dibenerin (lihat audit_nidn)."""
    if not user or not user.nidn:
        return None
    return DataDosen.objects.using('simda').filter(nidn=user.nidn).first()
