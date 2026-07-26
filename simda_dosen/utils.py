from django.shortcuts import get_object_or_404

from .models import DataDosen, JenisKepegawaianPublik, StatusKepegawaianPublik


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


def attach_kepegawaian_labels(users):
    """Tempel atribut .jenis_kepegawaian_nama, .status_kepegawaian_nama, dan
    ID identitas riset (.id_sinta, .id_scopus, .id_google_scholar, .orcid,
    .id_garuda) ke tiap User (role=dosen), dicocokkan lewat nidn ke DataDosen
    SIMDA. Dipakai di Kelola User/Rekap/Laporan supaya badge status & link
    riset bisa ditampilkan di daftar tanpa N+1 query per baris ke SIMDA.
    Return list (bukan queryset)."""
    users = list(users)
    nidn_set = {u.nidn for u in users if u.nidn}

    jenis_map = {j.id: j.nama for j in JenisKepegawaianPublik.objects.using('simda').all()}
    status_map = {s.id: s.nama for s in StatusKepegawaianPublik.objects.using('simda').all()}
    dosen_by_nidn = {}
    if nidn_set:
        dosen_by_nidn = {
            d.nidn: d for d in DataDosen.objects.using('simda').filter(nidn__in=nidn_set)
        }

    for u in users:
        d = dosen_by_nidn.get(u.nidn)
        u.jenis_kepegawaian_nama = jenis_map.get(d.jenis_kepegawaian_id, '') if d else ''
        u.status_kepegawaian_nama = status_map.get(d.status_kepegawaian_id, '') if d else ''
        u.id_sinta = d.id_sinta if d else ''
        u.id_scopus = d.id_scopus if d else ''
        u.id_google_scholar = d.id_google_scholar if d else ''
        u.orcid = d.orcid if d else ''
        u.id_garuda = d.id_garuda if d else ''
    return users


def filter_dosen_qs_by_kepegawaian(qs, jenis_kepegawaian_id='', status_kepegawaian_id=''):
    """Filter queryset User (role=dosen) berdasarkan field kepegawaian yang
    kini disimpan di DataDosen SIMDA, dicocokkan lewat nidn (User dan
    DataDosen ada di database berbeda, tidak bisa JOIN langsung)."""
    if not jenis_kepegawaian_id and not status_kepegawaian_id:
        return qs
    dosen_filter = {}
    if jenis_kepegawaian_id:
        dosen_filter['jenis_kepegawaian_id'] = jenis_kepegawaian_id
    if status_kepegawaian_id:
        dosen_filter['status_kepegawaian_id'] = status_kepegawaian_id
    nidn_list = list(
        DataDosen.objects.using('simda').filter(**dosen_filter).values_list('nidn', flat=True)
    )
    return qs.filter(nidn__in=nidn_list)
