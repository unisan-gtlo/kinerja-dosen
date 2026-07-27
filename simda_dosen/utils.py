import re

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect

from .models import (
    DataDosen, BidangKeahlian, BidangKeahlianPublik,
    JenisKepegawaianPublik, StatusKepegawaianPublik,
)


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
    """Tempel atribut .jenis_kepegawaian_nama, .status_kepegawaian_nama, ID
    identitas riset (.id_sinta, .id_scopus, .id_google_scholar, .orcid,
    .id_garuda), .nama_lengkap_gelar, dan .foto_url ke tiap User (role=dosen),
    dicocokkan lewat nidn ke DataDosen SIMDA. Dipakai di Kelola User/Rekap/
    Dashboard/Laporan supaya badge status, link riset, nama+gelar, dan foto
    bisa ditampilkan di daftar tanpa N+1 query per baris ke SIMDA.
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
        u.nama_dosen = d.nama_lengkap_gelar if d else (u.get_full_name() or u.username)
        u.foto_url = d.foto.url if d and d.foto else ''
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


def get_or_create_bidang_keahlian(nama):
    """Cari BidangKeahlian di SIMDA berdasarkan nama (case-insensitive) --
    kalau belum ada, buat baru otomatis (self-service, dipicu dosen
    mengetik nilai yang belum ada di daftar dropdown Bidang Keahlian/
    Keilmuan di Profil Dosen). Return id (int), atau None kalau nama
    kosong."""
    nama = (nama or '').strip()
    if not nama:
        return None

    existing = BidangKeahlianPublik.objects.using('simda').filter(nama__iexact=nama).first()
    if existing:
        return existing.id

    base_kode = re.sub(r'[^A-Z0-9]', '', nama.upper())[:16] or 'BK'
    kode = base_kode
    suffix = 1
    while BidangKeahlian.objects.using('simda').filter(kode=kode).exists():
        suffix += 1
        kode = f'{base_kode}{suffix}'[:20]

    baru = BidangKeahlian.objects.using('simda').create(
        kode=kode, nama=nama, rumpun_ilmu='', status=True
    )
    return baru.id


def sync_jabfung_aktif(profil):
    """Auto-update DataDosen.jabatan_fungsional_id dari Riwayat Jabatan
    Fungsional dosen -- pilih yang masih aktif (tgl_selesai kosong) dengan
    tmt paling akhir; kalau semua sudah ada tgl_selesai (tidak ada yang
    ongoing), pakai yang tmt-nya paling akhir. Dipanggil tiap kali riwayat
    jabfung ditambah/diedit/dihapus -- field ringkasan ini tidak perlu
    diverifikasi admin manual (beda dengan BKD yang memang butuh
    pengesahan berjenjang)."""
    aktif = profil.riwayat_jabfung.filter(tgl_selesai__isnull=True).order_by('-tmt').first()
    terbaru = aktif or profil.riwayat_jabfung.order_by('-tmt').first()
    profil.jabatan_fungsional_id = terbaru.jabatan_fungsional_id if terbaru else None
    profil.save(update_fields=['jabatan_fungsional_id'])


def sync_pendidikan_terakhir(profil):
    """Auto-update DataDosen.pendidikan_terakhir dari Riwayat Pendidikan
    dosen -- ambil jenjang dengan tahun_lulus paling akhir (harus sudah
    lulus, tahun_lulus terisi). Dipanggil tiap kali riwayat pendidikan
    ditambah/diedit/dihapus."""
    terbaru = profil.riwayat_pendidikan.filter(
        tahun_lulus__isnull=False
    ).order_by('-tahun_lulus').first()
    profil.pendidikan_terakhir = terbaru.jenjang if terbaru else ''
    profil.save(update_fields=['pendidikan_terakhir'])


def dapat_kelola_nidn(user, nidn):
    """Sama seperti User.dapat_kelola(), tapi target ditentukan lewat nidn --
    dipakai di record SIMDA (RiwayatJabatanFungsional/Pangkat/Pendidikan/BKD)
    yang tidak punya FK langsung ke accounts.User, cuma field dosen.nidn."""
    from accounts.models import User
    if user.nidn and user.nidn == nidn:
        return True
    target = User.objects.filter(nidn=nidn).first()
    return bool(target) and user.dapat_kelola(target)


def resolve_target_user(request, dosen_id, redirect_url_name):
    """Tentukan user yang datanya mau diedit lewat dosen_id (POST) --
    dosen_id cuma dipakai kalau pemohon boleh kelola dosen itu (lihat
    User.dapat_kelola), selain itu diedit ke diri sendiri. Return
    (target_user, error_response); error_response None kalau aman."""
    from accounts.models import User
    user = request.user
    if not dosen_id:
        return user, None
    target_user = get_object_or_404(User, id=dosen_id)
    if not user.dapat_kelola(target_user):
        messages.error(request, 'Anda tidak memiliki akses untuk mengelola data dosen ini.')
        return None, redirect(redirect_url_name)
    return target_user, None
