import re

from django.contrib import messages
from django.db import DatabaseError
from django.shortcuts import get_object_or_404, redirect
from django.test.testcases import DatabaseOperationForbidden
from django.urls import reverse

from .models import (
    DataDosen, DataTendik, BidangKeahlian, BidangKeahlianPublik, GolonganPublik,
    JenisKepegawaianPublik, PejabatStruktural, StatusKepegawaianPublik, UnitKerja,
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


def get_simda_tendik_or_none(user):
    """Versi tendik dari get_simda_dosen_or_none() -- dicocokkan lewat
    nip_yayasan (tendik tidak punya NIDN). Return None kalau nip_yayasan
    kosong atau tidak match ke SIMDA."""
    if not user or not user.nip_yayasan:
        return None
    return DataTendik.objects.using('simda').filter(nip_yayasan=user.nip_yayasan).first()


def attach_nama_resmi(users):
    """Tempel atribut `.nama_resmi` (nama asli dari SIMDA, bukan first_name/
    last_name akun login) ke tiap User dalam `users` -- dosen dicocokkan
    lewat nidn ke DataDosen, tendik lewat nip_yayasan ke DataTendik.
    Fallback ke get_full_name()/username kalau tidak ketemu di SIMDA sama
    sekali (mis. akun jabatan/administratif generik yang memang bukan
    representasi satu pegawai -- lihat CLAUDE.md, akun ini TIDAK akan
    pernah resolve ke SIMDA karena tidak mewakili satu NIDN/NIP tertentu).

    Dipakai laporan lintas-pegawai presensi (Internal/Bulanan Jam Kerja/
    Detail) supaya nama yang tampil akurat. Ditangkap DatabaseError sama
    seperti get_pejabat_aktif() -- kalau akses master.data_tendik belum
    di-grant di SIMDA, laporan tetap render pakai nama akun lokal
    (fallback), tidak 500. Ditangkap juga DatabaseOperationForbidden --
    ini BUKAN error koneksi sungguhan, tapi guard Django TestCase yang
    memblokir query ke alias database yang tidak dideklarasikan di
    `databases` test class (AssertionError, bukan turunan DatabaseError,
    jadi harus ditangkap eksplisit) -- fungsi ini dipanggil dari banyak
    test lama (LaporanBulananViewTest dkk.) yang ditulis sebelum fitur
    ini ada dan tidak mendeklarasikan 'simda', TIDAK pernah muncul di
    produksi (cuma ada di bawah Django test runner)."""
    users = list(users)
    nidn_list = [u.nidn for u in users if u.nidn]
    nip_list = [u.nip_yayasan for u in users if u.nip_yayasan]

    dosen_by_nidn, tendik_by_nip = {}, {}
    try:
        if nidn_list:
            dosen_by_nidn = {
                d.nidn: d for d in DataDosen.objects.using('simda').filter(nidn__in=nidn_list)
            }
        if nip_list:
            tendik_by_nip = {
                t.nip_yayasan: t for t in DataTendik.objects.using('simda').filter(nip_yayasan__in=nip_list)
            }
    except (DatabaseError, DatabaseOperationForbidden):
        pass

    for u in users:
        dosen = dosen_by_nidn.get(u.nidn) if u.nidn else None
        tendik = tendik_by_nip.get(u.nip_yayasan) if u.nip_yayasan else None
        if dosen:
            u.nama_resmi = dosen.nama_lengkap_gelar
        elif tendik:
            u.nama_resmi = tendik.nama_lengkap
        else:
            u.nama_resmi = u.get_full_name() or u.username
    return users


def attach_kepegawaian_labels(users):
    """Tempel atribut .jenis_kepegawaian_nama, .status_kepegawaian_nama, ID
    identitas riset (.id_sinta, .id_scopus, .id_google_scholar, .orcid,
    .id_garuda), .nama_lengkap_gelar, dan .foto_url ke tiap User.
    Dosen dicocokkan lewat nidn ke DataDosen SIMDA, tendik dicocokkan lewat
    nip_yayasan ke DataTendik SIMDA (jenis_kepegawaian_id/status_kepegawaian_id
    keduanya merujuk tabel referensi SIMDA yang sama, kepegawaian_ref, jadi
    jenis_map/status_map dipakai bareng). ID riset (SINTA/Scopus/dst) TETAP
    dosen-only -- tendik tidak punya konsep itu. Dipakai di Kelola User/
    Rekap/Dashboard/Laporan supaya badge status, link riset, nama+gelar, dan
    foto bisa ditampilkan di daftar tanpa N+1 query per baris ke SIMDA.
    Return list (bukan queryset)."""
    users = list(users)
    nidn_set = {u.nidn for u in users if u.nidn}
    nip_yayasan_set = {u.nip_yayasan for u in users if getattr(u, 'nip_yayasan', None)}

    jenis_map = {j.id: j.nama for j in JenisKepegawaianPublik.objects.using('simda').all()}
    status_map = {s.id: s.nama for s in StatusKepegawaianPublik.objects.using('simda').all()}
    dosen_by_nidn = {}
    if nidn_set:
        dosen_by_nidn = {
            d.nidn: d for d in DataDosen.objects.using('simda').filter(nidn__in=nidn_set)
        }
    tendik_by_nip_yayasan = {}
    if nip_yayasan_set:
        tendik_by_nip_yayasan = {
            t.nip_yayasan: t for t in DataTendik.objects.using('simda').filter(nip_yayasan__in=nip_yayasan_set)
        }

    for u in users:
        d = dosen_by_nidn.get(u.nidn)
        t = None if d else tendik_by_nip_yayasan.get(u.nip_yayasan)
        sumber = d or t
        u.jenis_kepegawaian_nama = jenis_map.get(sumber.jenis_kepegawaian_id, '') if sumber else ''
        u.status_kepegawaian_nama = status_map.get(sumber.status_kepegawaian_id, '') if sumber else ''
        u.id_sinta = d.id_sinta if d else ''
        u.id_scopus = d.id_scopus if d else ''
        u.id_google_scholar = d.id_google_scholar if d else ''
        u.orcid = d.orcid if d else ''
        u.id_garuda = d.id_garuda if d else ''
        u.nama_dosen = d.nama_lengkap_gelar if d else (t.nama_lengkap if t else (u.get_full_name() or u.username))
        u.foto_url = (d.foto.url if d and d.foto else (t.foto.url if t and t.foto else ''))
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


def get_or_create_unit_kerja(nama):
    """Cari UnitKerja di SIMDA berdasarkan nama (case-insensitive) --
    kalau belum ada, buat baru otomatis (dipicu admin mengetik nilai
    yang belum ada di dropdown Unit Kerja di form Kelola Data Tendik).
    Return id (int), atau None kalau nama kosong. `jenis` default
    'administrasi' (paling umum untuk unit kerja baru yang diketik
    manual di form ini) -- bisa diubah lewat Django Admin SIMDA kalau
    perlu jenis lain."""
    nama = (nama or '').strip()
    if not nama:
        return None

    existing = UnitKerja.objects.using('simda').filter(nama__iexact=nama).first()
    if existing:
        return existing.id

    base_kode = re.sub(r'[^A-Z0-9]', '', nama.upper())[:16] or 'UK'
    kode = base_kode
    suffix = 1
    while UnitKerja.objects.using('simda').filter(kode=kode).exists():
        suffix += 1
        kode = f'{base_kode}{suffix}'[:20]

    baru = UnitKerja.objects.using('simda').create(
        kode=kode, nama=nama, jenis='administrasi', status=True
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


def get_golongan_ref_list_dosen():
    """Daftar Golongan untuk dropdown Riwayat Pangkat/Golongan DOSEN --
    difilter mulai dari IIIa ke atas (dosen minimal S1, golongan I/II
    itu skala PNS non-sarjana/tendik, tidak relevan untuk dosen). Kode
    di data referensi formatnya tanpa garis miring (mis. 'IIIa', bukan
    'III/a') -- kalau entah kenapa tidak ketemu, aman kembalikan daftar
    penuh (jangan sampai dropdown malah kosong)."""
    qs = GolonganPublik.objects.using('simda').all()
    batas = qs.filter(kode__iexact='IIIa').first()
    if not batas:
        return qs
    return qs.filter(urutan__gte=batas.urutan)


def sync_golongan_terakhir(profil):
    """Auto-update DataDosen.golongan_id dari Riwayat Pangkat/Golongan
    dosen -- ambil yang TMT-nya paling akhir (tidak ada konsep tgl_selesai
    di riwayat ini, beda dengan jabfung). Dipanggil tiap kali riwayat
    pangkat/golongan ditambah/diedit/dihapus."""
    terbaru = profil.riwayat_pangkat_golongan.order_by('-tmt').first()
    profil.golongan_id = terbaru.golongan_id if terbaru else None
    profil.save(update_fields=['golongan_id'])


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


def bisa_tambah_tridarma(user, target_user):
    """Tambah (create) data Profil/Tri Dharma dibatasi LEBIH KETAT dari
    dapat_kelola() biasa (yang tetap dipakai apa adanya untuk Edit/Hapus):
    menambahkan data ATAS NAMA dosen lain cuma boleh admin/operator --
    dekan/wadek/kaprodi/sekprodi/rektorat/biro TIDAK LAGI bisa (per
    2026-08-03), meski dapat_kelola() masih True untuk mereka (dipakai
    Edit/Hapus data yang sudah ada). Data diri sendiri (self-service)
    TETAP boleh ditambahkan siapa pun, tidak terpengaruh pembatasan ini."""
    if user.id == target_user.id:
        return True
    return user.role in ('admin', 'operator') and user.dapat_kelola(target_user)


def resolve_target_user_tambah(request, dosen_id, redirect_url_name):
    """Sama seperti resolve_target_user(), TAPI khusus untuk aksi TAMBAH
    (create) -- dibatasi lewat bisa_tambah_tridarma() (lihat
    dokumentasinya), bukan cuma dapat_kelola() biasa."""
    from accounts.models import User
    user = request.user
    if not dosen_id:
        return user, None
    target_user = get_object_or_404(User, id=dosen_id)
    if not bisa_tambah_tridarma(user, target_user):
        messages.error(request, 'Hanya admin/operator yang bisa menambahkan data untuk dosen lain.')
        return None, redirect(redirect_url_name)
    return target_user, None


def user_id_dari_nidn(nidn):
    """Riwayat Jabfung/Pangkat/Pendidikan Dosen & BKD (SIMDA) cuma punya
    dosen.nidn, bukan FK ke accounts.User -- dipakai supaya redirect_ke()
    tetap bisa menyertakan ?dosen_id= setelah Tambah/Edit/Hapus riwayat
    ini (lihat profil/views.py dan kinerja/views.py)."""
    from accounts.models import User
    u = User.objects.filter(nidn=nidn).first()
    return u.id if u else None


def redirect_ke(url_name, request_user, target_user_id=None):
    """redirect() ke url_name, menambahkan ?dosen_id=<id> kalau target
    BUKAN diri sendiri -- dipakai di SEMUA tambah_*/edit_*/hapus_* Tri
    Dharma (2026-08-07) supaya identitas dosen yang sedang dikelola
    admin/operator/dekan/dst TIDAK hilang setelah simpan (sebelumnya
    redirect selalu polos ke url_name, jadi setelah Tambah/Edit malah
    balik ke data milik sendiri, harus kembali ke Rekap Data untuk cari
    dosen itu lagi). Pola query string ini SAMA dengan href sidebar di
    templates/base.html (`?dosen_id={{ target_user.id }}`) dan sama-sama
    dibaca oleh semua view index() lewat request.GET.get('dosen_id').
    target_user_id boleh None/kosong (redirect polos, dipakai request
    milik diri sendiri)."""
    if target_user_id and target_user_id != request_user.id:
        return redirect(f'{reverse(url_name)}?dosen_id={target_user_id}')
    return redirect(url_name)


def get_pejabat_aktif(nama_jabatan):
    """Cari pejabat struktural yang SEDANG aktif menjabat `nama_jabatan`
    (mis. "Rektor") -- dipakai untuk mengambil otomatis nama+NIP+gambar
    tanda tangan (file_ttd) buat blok tanda tangan laporan resmi (lihat
    presensi/laporan_serdos.py). Return None kalau belum di-setup di
    SIMDA (mis. akses master.pejabat_struktural belum di-grant, lihat
    tambah_akses_pejabat_struktural.sql di repo SIMDA -- ditangkap
    eksplisit di sini, DatabaseError, supaya belum di-grant tidak bikin
    seluruh halaman laporan 500, cukup dianggap belum ada pejabat aktif
    dan form tetap bisa diisi manual) atau memang belum ada baris aktif
    untuk jabatan itu. Koneksi 'simda' jalan di mode autocommit (tidak
    ada ATOMIC_REQUESTS di settings), jadi aman ditangkap di sini tanpa
    perlu rollback manual -- tidak meracuni query lain di request yang sama."""
    try:
        return (
            PejabatStruktural.objects.using('simda')
            .filter(jabatan__nama__iexact=nama_jabatan, is_aktif=True)
            .select_related('jabatan', 'dosen', 'tendik')
            .first()
        )
    except DatabaseError:
        return None
