from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from master.models import TahunAkademik, Pengaturan
from accounts.models import User
from simda_dosen.models import DataDosen, MahasiswaPublik
from simda_dosen.utils import get_simda_dosen_or_none
from kinerja.utils import attach_dokumen_count
from .models import (
    Penelitian, AnggotaPenelitian, PublikasiKarya, PenulisPublikasiKarya,
    PatenHki, PenulisPatenHki,
)

PER_PAGE_CHOICES = [10, 20, 50, 100]
DEFAULT_PER_PAGE = 20


def cek_status_input():
    try:
        p = Pengaturan.objects.first()
        return p.status_input == 'buka' if p else True
    except:
        return True


def _target_user(request, from_post=False):
    user = request.user
    source = request.POST if from_post else request.GET
    dosen_id = source.get('dosen_id')
    if dosen_id and user.role in ['admin', 'kaprodi', 'sekprodi', 'operator', 'dekan', 'wadek', 'rektorat', 'biro']:
        return get_object_or_404(User, id=dosen_id)
    return user


def _paginate(request, qs, page_param, per_page):
    paginator = Paginator(qs, per_page)
    return paginator.get_page(request.GET.get(page_param, 1))


def _co_author_queryset(model, target_user, member_related_name, jenis_field='jenis_penulis'):
    """Record milik target_user sendiri, ditambah record dosen lain yang
    mencantumkan target_user sebagai anggota/penulis Dosen (co-author) --
    supaya karya bersama ikut terhitung kinerja semua dosen penulisnya.
    Sama pola dengan Bahan Ajar (lihat pendidikan/views.py)."""
    qs = model.objects.filter(user=target_user)
    dosen = get_simda_dosen_or_none(target_user)
    if dosen:
        filter_kwargs = {
            f'{member_related_name}__{jenis_field}': 'dosen',
            f'{member_related_name}__dosen_id': dosen.id,
        }
        qs = qs | model.objects.filter(**filter_kwargs)
    return qs.select_related('user').distinct()


def _attach_co_penulis(page_obj, target_user):
    for o in page_obj.object_list:
        o.co_penulis = (o.user_id != target_user.id)
    return page_obj


@login_required
def index(request):
    user = request.user
    target_user = _target_user(request)

    tahun_list = TahunAkademik.objects.filter(status='aktif').order_by('-urutan')
    input_terbuka = cek_status_input()
    bisa_edit = (user == target_user or user.role in ['admin', 'operator']) and input_terbuka

    try:
        per_page = int(request.GET.get('per_page', DEFAULT_PER_PAGE))
    except (TypeError, ValueError):
        per_page = DEFAULT_PER_PAGE
    if per_page not in PER_PAGE_CHOICES:
        per_page = DEFAULT_PER_PAGE

    penelitian_qs = _co_author_queryset(Penelitian, target_user, 'anggota_set', 'jenis_anggota')
    publikasi_qs = _co_author_queryset(PublikasiKarya, target_user, 'penulis_set')
    paten_qs = _co_author_queryset(PatenHki, target_user, 'penulis_set')

    penelitian_page = _paginate(request, penelitian_qs, 'page_pen', per_page)
    publikasi_page = _paginate(request, publikasi_qs, 'page_pub', per_page)
    paten_page = _paginate(request, paten_qs, 'page_pat', per_page)

    _attach_co_penulis(penelitian_page, target_user)
    _attach_co_penulis(publikasi_page, target_user)
    _attach_co_penulis(paten_page, target_user)

    attach_dokumen_count(penelitian_page.object_list, 'penelitian')
    attach_dokumen_count(publikasi_page.object_list, 'publikasi')
    attach_dokumen_count(paten_page.object_list, 'hki')

    context = {
        'target_user': target_user,
        'tahun_list': tahun_list,
        'bisa_edit': bisa_edit,
        'input_terbuka': input_terbuka,
        'per_page': per_page,
        'per_page_choices': PER_PAGE_CHOICES,
        'penelitian_list': penelitian_page,
        'publikasi_list': publikasi_page,
        'paten_list': paten_page,
    }
    return render(request, 'penelitian/index.html', context)


# ============================================================
# PENELITIAN
# ============================================================

@login_required
def tambah_penelitian(request):
    if request.method != 'POST':
        return redirect('penelitian:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('penelitian:index')

    target_user = _target_user(request, from_post=True)
    Penelitian.objects.create(
        user=target_user,
        kode_prodi=target_user.kode_prodi or '',
        kode_fakultas=target_user.kode_fakultas or '',
        kategori_pelaksanaan=request.POST.get('kategori_pelaksanaan', ''),
        judul_kegiatan=request.POST.get('judul_kegiatan', '').strip(),
        afiliasi=request.POST.get('afiliasi', '').strip(),
        kelompok_bidang=request.POST.get('kelompok_bidang', '').strip(),
        litabmas_sebelumnya=request.POST.get('litabmas_sebelumnya', '').strip(),
        jenis_skim=request.POST.get('jenis_skim', '').strip(),
        lokasi_kegiatan=request.POST.get('lokasi_kegiatan', '').strip(),
        tahun_usulan=request.POST.get('tahun_usulan') or None,
        tahun_kegiatan=request.POST.get('tahun_kegiatan', '').strip(),
        tahun_pelaksanaan=request.POST.get('tahun_pelaksanaan') or None,
        lama_kegiatan_tahun=request.POST.get('lama_kegiatan_tahun') or 1,
        tahun_pelaksanaan_ke=request.POST.get('tahun_pelaksanaan_ke') or 1,
        dana_dikti=request.POST.get('dana_dikti') or 0,
        dana_pt=request.POST.get('dana_pt') or 0,
        dana_institusi_lain=request.POST.get('dana_institusi_lain') or 0,
        in_kind=request.POST.get('in_kind', '').strip(),
        no_sk_penugasan=request.POST.get('no_sk_penugasan', '').strip(),
        tanggal_sk_penugasan=request.POST.get('tanggal_sk_penugasan') or None,
        mitra_litabmas=request.POST.get('mitra_litabmas', '').strip(),
        semester=request.POST.get('semester', ''),
        tahun_akademik=request.POST.get('tahun_akademik', ''),
        updated_by=request.user.username,
    )
    messages.success(request, 'Data penelitian berhasil ditambahkan.')
    return redirect('penelitian:index')


@login_required
def edit_penelitian(request, id):
    obj = get_object_or_404(Penelitian, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('penelitian:index')
    if request.method == 'POST':
        obj.kategori_pelaksanaan = request.POST.get('kategori_pelaksanaan', obj.kategori_pelaksanaan)
        obj.judul_kegiatan = request.POST.get('judul_kegiatan', '').strip()
        obj.afiliasi = request.POST.get('afiliasi', '').strip()
        obj.kelompok_bidang = request.POST.get('kelompok_bidang', '').strip()
        obj.litabmas_sebelumnya = request.POST.get('litabmas_sebelumnya', '').strip()
        obj.jenis_skim = request.POST.get('jenis_skim', '').strip()
        obj.lokasi_kegiatan = request.POST.get('lokasi_kegiatan', '').strip()
        obj.tahun_usulan = request.POST.get('tahun_usulan') or obj.tahun_usulan
        obj.tahun_kegiatan = request.POST.get('tahun_kegiatan', '').strip() or obj.tahun_kegiatan
        obj.tahun_pelaksanaan = request.POST.get('tahun_pelaksanaan') or obj.tahun_pelaksanaan
        obj.lama_kegiatan_tahun = request.POST.get('lama_kegiatan_tahun') or obj.lama_kegiatan_tahun
        obj.tahun_pelaksanaan_ke = request.POST.get('tahun_pelaksanaan_ke') or obj.tahun_pelaksanaan_ke
        obj.dana_dikti = request.POST.get('dana_dikti') or 0
        obj.dana_pt = request.POST.get('dana_pt') or 0
        obj.dana_institusi_lain = request.POST.get('dana_institusi_lain') or 0
        obj.in_kind = request.POST.get('in_kind', '').strip()
        obj.no_sk_penugasan = request.POST.get('no_sk_penugasan', '').strip()
        obj.tanggal_sk_penugasan = request.POST.get('tanggal_sk_penugasan') or None
        obj.mitra_litabmas = request.POST.get('mitra_litabmas', '').strip()
        obj.semester = request.POST.get('semester', '')
        obj.tahun_akademik = request.POST.get('tahun_akademik', obj.tahun_akademik)
        obj.updated_by = request.user.username
        obj.save()
        messages.success(request, 'Data penelitian berhasil diupdate.')
    return redirect('penelitian:index')


@login_required
def hapus_penelitian(request, id):
    obj = get_object_or_404(Penelitian, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('penelitian:index')
    obj.delete()
    messages.success(request, 'Data penelitian berhasil dihapus.')
    return redirect('penelitian:index')


@login_required
def kelola_anggota_penelitian(request, penelitian_id):
    penelitian = get_object_or_404(Penelitian, id=penelitian_id)
    user = request.user
    bisa_edit = (user == penelitian.user or user.role in ['admin', 'operator']) and cek_status_input()

    if penelitian.user != user and user.role not in ['admin', 'operator']:
        dosen = get_simda_dosen_or_none(user)
        is_co = dosen and penelitian.anggota_set.filter(jenis_anggota='dosen', dosen_id=dosen.id).exists()
        if not is_co:
            messages.error(request, 'Tidak memiliki akses.')
            return redirect('penelitian:index')

    if request.method == 'POST':
        aksi = request.POST.get('aksi')

        if aksi == 'tambah':
            if not bisa_edit:
                messages.error(request, 'Input data sedang dikunci.')
                return redirect('penelitian:kelola_anggota_penelitian', penelitian_id=penelitian_id)

            jenis_anggota = request.POST.get('jenis_anggota', '')
            anggota = AnggotaPenelitian(
                penelitian=penelitian,
                jenis_anggota=jenis_anggota,
                peran=request.POST.get('peran', 'anggota'),
                status_aktif=bool(request.POST.get('status_aktif')),
                updated_by=user.username,
            )
            if jenis_anggota == 'dosen':
                dosen_id = request.POST.get('dosen_id')
                dosen = get_object_or_404(DataDosen.objects.using('simda'), id=dosen_id) if dosen_id else None
                if not dosen:
                    messages.error(request, 'Nama dosen wajib dipilih.')
                    return redirect('penelitian:kelola_anggota_penelitian', penelitian_id=penelitian_id)
                anggota.dosen_id = dosen.id
                anggota.nama = dosen.nama_lengkap_gelar
                anggota.nidn_nim = dosen.nidn
                anggota.perguruan_tinggi = 'Universitas Ichsan Gorontalo'
            elif jenis_anggota == 'mahasiswa':
                mhs_id = request.POST.get('mahasiswa_id')
                mhs = get_object_or_404(MahasiswaPublik.objects.using('simda'), id=mhs_id) if mhs_id else None
                if not mhs:
                    messages.error(request, 'Nama mahasiswa wajib dipilih.')
                    return redirect('penelitian:kelola_anggota_penelitian', penelitian_id=penelitian_id)
                anggota.mahasiswa_id = mhs.id
                anggota.nama = mhs.nama_lengkap
                anggota.nidn_nim = mhs.nim
            else:
                nama = request.POST.get('nama', '').strip()
                if not nama:
                    messages.error(request, 'Nama kolaborator wajib diisi.')
                    return redirect('penelitian:kelola_anggota_penelitian', penelitian_id=penelitian_id)
                anggota.nama = nama
                anggota.perguruan_tinggi = request.POST.get('perguruan_tinggi_lain', '').strip()

            anggota.save()
            messages.success(request, f'Anggota "{anggota.nama}" berhasil ditambahkan.')

        elif aksi == 'edit':
            if not bisa_edit:
                messages.error(request, 'Input data sedang dikunci.')
                return redirect('penelitian:kelola_anggota_penelitian', penelitian_id=penelitian_id)
            anggota = get_object_or_404(AnggotaPenelitian, id=request.POST.get('anggota_id'), penelitian=penelitian)
            anggota.peran = request.POST.get('peran', anggota.peran)
            anggota.status_aktif = bool(request.POST.get('status_aktif'))
            if anggota.jenis_anggota == 'kolaborator_eksternal':
                anggota.nama = request.POST.get('nama', '').strip() or anggota.nama
                anggota.perguruan_tinggi = request.POST.get('perguruan_tinggi_lain', '').strip()
            anggota.updated_by = user.username
            anggota.save()
            messages.success(request, 'Data anggota berhasil diupdate.')

        elif aksi == 'hapus':
            anggota = get_object_or_404(AnggotaPenelitian, id=request.POST.get('anggota_id'), penelitian=penelitian)
            if bisa_edit:
                nama = anggota.nama
                anggota.delete()
                messages.success(request, f'Anggota "{nama}" berhasil dihapus.')
            else:
                messages.error(request, 'Tidak memiliki akses.')

        return redirect('penelitian:kelola_anggota_penelitian', penelitian_id=penelitian_id)

    context = {
        'penelitian': penelitian,
        'bisa_edit': bisa_edit,
        'anggota_list': penelitian.anggota_set.all(),
    }
    return render(request, 'penelitian/kelola_anggota_penelitian.html', context)


# ============================================================
# PUBLIKASI KARYA
# ============================================================

@login_required
def tambah_publikasi(request):
    if request.method != 'POST':
        return redirect('penelitian:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('penelitian:index')

    target_user = _target_user(request, from_post=True)
    PublikasiKarya.objects.create(
        user=target_user,
        kode_prodi=target_user.kode_prodi or '',
        kode_fakultas=target_user.kode_fakultas or '',
        jenis=request.POST.get('jenis', ''),
        kategori_capaian=request.POST.get('kategori_capaian', '').strip(),
        aktivitas_litabmas=request.POST.get('aktivitas_litabmas', '').strip(),
        judul_artikel=request.POST.get('judul_artikel', '').strip(),
        nama_seminar=request.POST.get('nama_seminar', '').strip(),
        tanggal_terbit=request.POST.get('tanggal_terbit') or None,
        penerbit_penyelenggara=request.POST.get('penerbit_penyelenggara', '').strip(),
        kota_penyelenggaraan=request.POST.get('kota_penyelenggaraan', '').strip(),
        apakah_seminar=bool(request.POST.get('apakah_seminar')),
        apakah_prosiding=bool(request.POST.get('apakah_prosiding')),
        bahasa=request.POST.get('bahasa', '').strip(),
        isbn=request.POST.get('isbn', '').strip(),
        issn=request.POST.get('issn', '').strip(),
        e_issn=request.POST.get('e_issn', '').strip(),
        tautan_eksternal=request.POST.get('tautan_eksternal', '').strip(),
        keterangan=request.POST.get('keterangan', '').strip(),
        semester=request.POST.get('semester', ''),
        tahun_akademik=request.POST.get('tahun_akademik', ''),
        updated_by=request.user.username,
    )
    messages.success(request, 'Data publikasi karya berhasil ditambahkan.')
    return redirect('penelitian:index')


@login_required
def edit_publikasi(request, id):
    obj = get_object_or_404(PublikasiKarya, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('penelitian:index')
    if request.method == 'POST':
        obj.jenis = request.POST.get('jenis', obj.jenis)
        obj.kategori_capaian = request.POST.get('kategori_capaian', '').strip()
        obj.aktivitas_litabmas = request.POST.get('aktivitas_litabmas', '').strip()
        obj.judul_artikel = request.POST.get('judul_artikel', '').strip()
        obj.nama_seminar = request.POST.get('nama_seminar', '').strip()
        obj.tanggal_terbit = request.POST.get('tanggal_terbit') or obj.tanggal_terbit
        obj.penerbit_penyelenggara = request.POST.get('penerbit_penyelenggara', '').strip()
        obj.kota_penyelenggaraan = request.POST.get('kota_penyelenggaraan', '').strip()
        obj.apakah_seminar = bool(request.POST.get('apakah_seminar'))
        obj.apakah_prosiding = bool(request.POST.get('apakah_prosiding'))
        obj.bahasa = request.POST.get('bahasa', '').strip()
        obj.isbn = request.POST.get('isbn', '').strip()
        obj.issn = request.POST.get('issn', '').strip()
        obj.e_issn = request.POST.get('e_issn', '').strip()
        obj.tautan_eksternal = request.POST.get('tautan_eksternal', '').strip()
        obj.keterangan = request.POST.get('keterangan', '').strip()
        obj.semester = request.POST.get('semester', '')
        obj.tahun_akademik = request.POST.get('tahun_akademik', obj.tahun_akademik)
        obj.updated_by = request.user.username
        obj.save()
        messages.success(request, 'Data publikasi karya berhasil diupdate.')
    return redirect('penelitian:index')


@login_required
def hapus_publikasi(request, id):
    obj = get_object_or_404(PublikasiKarya, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('penelitian:index')
    obj.delete()
    messages.success(request, 'Data publikasi karya berhasil dihapus.')
    return redirect('penelitian:index')


# ============================================================
# PATEN/HKI
# ============================================================

@login_required
def tambah_paten(request):
    if request.method != 'POST':
        return redirect('penelitian:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('penelitian:index')

    target_user = _target_user(request, from_post=True)
    PatenHki.objects.create(
        user=target_user,
        kode_prodi=target_user.kode_prodi or '',
        kode_fakultas=target_user.kode_fakultas or '',
        jenis=request.POST.get('jenis', ''),
        kategori_capaian=request.POST.get('kategori_capaian', '').strip(),
        aktivitas_litabmas=request.POST.get('aktivitas_litabmas', '').strip(),
        judul_karya=request.POST.get('judul_karya', '').strip(),
        tanggal=request.POST.get('tanggal') or None,
        penyelenggara=request.POST.get('penyelenggara', '').strip(),
        tautan_eksternal=request.POST.get('tautan_eksternal', '').strip(),
        keterangan=request.POST.get('keterangan', '').strip(),
        semester=request.POST.get('semester', ''),
        tahun_akademik=request.POST.get('tahun_akademik', ''),
        updated_by=request.user.username,
    )
    messages.success(request, 'Data Paten/HKI berhasil ditambahkan.')
    return redirect('penelitian:index')


@login_required
def edit_paten(request, id):
    obj = get_object_or_404(PatenHki, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('penelitian:index')
    if request.method == 'POST':
        obj.jenis = request.POST.get('jenis', obj.jenis)
        obj.kategori_capaian = request.POST.get('kategori_capaian', '').strip()
        obj.aktivitas_litabmas = request.POST.get('aktivitas_litabmas', '').strip()
        obj.judul_karya = request.POST.get('judul_karya', '').strip()
        obj.tanggal = request.POST.get('tanggal') or obj.tanggal
        obj.penyelenggara = request.POST.get('penyelenggara', '').strip()
        obj.tautan_eksternal = request.POST.get('tautan_eksternal', '').strip()
        obj.keterangan = request.POST.get('keterangan', '').strip()
        obj.semester = request.POST.get('semester', '')
        obj.tahun_akademik = request.POST.get('tahun_akademik', obj.tahun_akademik)
        obj.updated_by = request.user.username
        obj.save()
        messages.success(request, 'Data Paten/HKI berhasil diupdate.')
    return redirect('penelitian:index')


@login_required
def hapus_paten(request, id):
    obj = get_object_or_404(PatenHki, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('penelitian:index')
    obj.delete()
    messages.success(request, 'Data Paten/HKI berhasil dihapus.')
    return redirect('penelitian:index')


def _kelola_penulis(request, obj, penulis_related, fk_field, id_field, template, redirect_url_name):
    """Kelola Penulis Dosen/Mahasiswa/Lain generik, dipakai untuk Publikasi
    Karya dan Paten/HKI (struktur penulisnya identik). fk_field = nama field
    FK di model Penulis (mis. 'publikasi' atau 'paten_hki'), id_field = nama
    kwarg URL (mis. 'publikasi_id' atau 'paten_id')."""
    user = request.user
    bisa_edit = (user == obj.user or user.role in ['admin', 'operator']) and cek_status_input()

    if obj.user != user and user.role not in ['admin', 'operator']:
        dosen = get_simda_dosen_or_none(user)
        is_co = dosen and penulis_related.filter(jenis_penulis='dosen', dosen_id=dosen.id).exists()
        if not is_co:
            messages.error(request, 'Tidak memiliki akses.')
            return redirect('penelitian:index')

    PenulisModel = penulis_related.model

    if request.method == 'POST':
        aksi = request.POST.get('aksi')

        if aksi == 'tambah':
            if not bisa_edit:
                messages.error(request, 'Input data sedang dikunci.')
                return redirect(redirect_url_name, **{id_field: obj.id})

            jenis_penulis = request.POST.get('jenis_penulis', '')
            kwargs = {
                fk_field: obj,
                'jenis_penulis': jenis_penulis,
                'urutan': request.POST.get('urutan') or 1,
                'afiliasi': request.POST.get('afiliasi', '').strip(),
                'peran': request.POST.get('peran', 'anggota_penulis'),
                'corresponding_author': bool(request.POST.get('corresponding_author')),
                'updated_by': user.username,
            }
            penulis = PenulisModel(**kwargs)

            if jenis_penulis == 'dosen':
                dosen_id = request.POST.get('dosen_id')
                dosen = get_object_or_404(DataDosen.objects.using('simda'), id=dosen_id) if dosen_id else None
                if not dosen:
                    messages.error(request, 'Nama dosen wajib dipilih.')
                    return redirect(redirect_url_name, **{id_field: obj.id})
                penulis.dosen_id = dosen.id
                penulis.nama = dosen.nama_lengkap_gelar
                penulis.nidn_nim = dosen.nidn
                penulis.afiliasi = penulis.afiliasi or 'Universitas Ichsan Gorontalo'
            elif jenis_penulis == 'mahasiswa':
                mhs_id = request.POST.get('mahasiswa_id')
                mhs = get_object_or_404(MahasiswaPublik.objects.using('simda'), id=mhs_id) if mhs_id else None
                if not mhs:
                    messages.error(request, 'Nama mahasiswa wajib dipilih.')
                    return redirect(redirect_url_name, **{id_field: obj.id})
                penulis.mahasiswa_id = mhs.id
                penulis.nama = mhs.nama_lengkap
                penulis.nidn_nim = mhs.nim
            else:
                nama = request.POST.get('nama', '').strip()
                if not nama:
                    messages.error(request, 'Nama penulis wajib diisi.')
                    return redirect(redirect_url_name, **{id_field: obj.id})
                penulis.nama = nama

            penulis.save()
            messages.success(request, f'Penulis "{penulis.nama}" berhasil ditambahkan.')

        elif aksi == 'edit':
            if not bisa_edit:
                messages.error(request, 'Input data sedang dikunci.')
                return redirect(redirect_url_name, **{id_field: obj.id})
            penulis = get_object_or_404(PenulisModel, id=request.POST.get('penulis_id'))
            penulis.urutan = request.POST.get('urutan') or penulis.urutan
            penulis.afiliasi = request.POST.get('afiliasi', '').strip()
            penulis.peran = request.POST.get('peran', penulis.peran)
            penulis.corresponding_author = bool(request.POST.get('corresponding_author'))
            if penulis.jenis_penulis == 'lain':
                penulis.nama = request.POST.get('nama', '').strip() or penulis.nama
            penulis.updated_by = user.username
            penulis.save()
            messages.success(request, 'Data penulis berhasil diupdate.')

        elif aksi == 'hapus':
            penulis = get_object_or_404(PenulisModel, id=request.POST.get('penulis_id'))
            if bisa_edit:
                nama = penulis.nama
                penulis.delete()
                messages.success(request, f'Penulis "{nama}" berhasil dihapus.')
            else:
                messages.error(request, 'Tidak memiliki akses.')

        return redirect(redirect_url_name, **{id_field: obj.id})

    context = {
        'obj': obj,
        'bisa_edit': bisa_edit,
        'penulis_list': penulis_related.all(),
    }
    return render(request, template, context)


@login_required
def kelola_penulis_publikasi(request, publikasi_id):
    obj = get_object_or_404(PublikasiKarya, id=publikasi_id)
    return _kelola_penulis(
        request, obj, obj.penulis_set, 'publikasi', 'publikasi_id',
        'penelitian/kelola_penulis_publikasi.html', 'penelitian:kelola_penulis_publikasi'
    )


@login_required
def kelola_penulis_paten(request, paten_id):
    obj = get_object_or_404(PatenHki, id=paten_id)
    return _kelola_penulis(
        request, obj, obj.penulis_set, 'paten_hki', 'paten_id',
        'penelitian/kelola_penulis_paten.html', 'penelitian:kelola_penulis_paten'
    )
