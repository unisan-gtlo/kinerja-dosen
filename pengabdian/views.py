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
    Pengabdian, AnggotaPengabdian, Pembicara, PengelolaJurnal, JabatanStruktural,
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


def _co_author_queryset(model, target_user, member_related_name):
    """Record milik target_user sendiri, ditambah record dosen lain yang
    mencantumkan target_user sebagai anggota Dosen (co-author) -- sama pola
    dengan Penelitian (lihat penelitian/views.py)."""
    qs = model.objects.filter(user=target_user)
    dosen = get_simda_dosen_or_none(target_user)
    if dosen:
        filter_kwargs = {
            f'{member_related_name}__jenis_anggota': 'dosen',
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
    bisa_edit = user.dapat_kelola(target_user) and input_terbuka

    try:
        per_page = int(request.GET.get('per_page', DEFAULT_PER_PAGE))
    except (TypeError, ValueError):
        per_page = DEFAULT_PER_PAGE
    if per_page not in PER_PAGE_CHOICES:
        per_page = DEFAULT_PER_PAGE

    pengabdian_qs = _co_author_queryset(Pengabdian, target_user, 'anggota_set')
    pembicara_qs = Pembicara.objects.filter(user=target_user)
    jurnal_qs = PengelolaJurnal.objects.filter(user=target_user)
    jabatan_qs = JabatanStruktural.objects.filter(user=target_user)

    pengabdian_page = _paginate(request, pengabdian_qs, 'page_pkm', per_page)
    pembicara_page = _paginate(request, pembicara_qs, 'page_bic', per_page)
    jurnal_page = _paginate(request, jurnal_qs, 'page_jur', per_page)
    jabatan_page = _paginate(request, jabatan_qs, 'page_jab', per_page)

    _attach_co_penulis(pengabdian_page, target_user)

    attach_dokumen_count(pengabdian_page.object_list, 'pkm')
    attach_dokumen_count(pembicara_page.object_list, 'pembicara')
    attach_dokumen_count(jurnal_page.object_list, 'pengelola_jurnal')
    attach_dokumen_count(jabatan_page.object_list, 'jabatan_struktural')

    context = {
        'target_user': target_user,
        'tahun_list': tahun_list,
        'bisa_edit': bisa_edit,
        'input_terbuka': input_terbuka,
        'per_page': per_page,
        'per_page_choices': PER_PAGE_CHOICES,
        'pengabdian_list': pengabdian_page,
        'pembicara_list': pembicara_page,
        'jurnal_list': jurnal_page,
        'jabatan_list': jabatan_page,
    }
    return render(request, 'pengabdian/index.html', context)


# ============================================================
# PENGABDIAN
# ============================================================

@login_required
def tambah_pengabdian(request):
    if request.method != 'POST':
        return redirect('pengabdian:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('pengabdian:index')

    target_user = _target_user(request, from_post=True)
    Pengabdian.objects.create(
        user=target_user,
        kode_prodi=target_user.kode_prodi or '',
        kode_fakultas=target_user.kode_fakultas or '',
        kategori_kegiatan=request.POST.get('kategori_kegiatan', ''),
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
        no_sk_penugasan=request.POST.get('no_sk_penugasan', '').strip(),
        tanggal_sk_penugasan=request.POST.get('tanggal_sk_penugasan') or None,
        mitra_litabmas=request.POST.get('mitra_litabmas', '').strip(),
        semester=request.POST.get('semester', ''),
        tahun_akademik=request.POST.get('tahun_akademik', ''),
        updated_by=request.user.username,
    )
    messages.success(request, 'Data pengabdian berhasil ditambahkan.')
    return redirect('pengabdian:index')


@login_required
def edit_pengabdian(request, id):
    obj = get_object_or_404(Pengabdian, id=id)
    if not request.user.dapat_kelola(obj.user):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('pengabdian:index')
    if request.method == 'POST':
        obj.kategori_kegiatan = request.POST.get('kategori_kegiatan', obj.kategori_kegiatan)
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
        obj.no_sk_penugasan = request.POST.get('no_sk_penugasan', '').strip()
        obj.tanggal_sk_penugasan = request.POST.get('tanggal_sk_penugasan') or None
        obj.mitra_litabmas = request.POST.get('mitra_litabmas', '').strip()
        obj.semester = request.POST.get('semester', '')
        obj.tahun_akademik = request.POST.get('tahun_akademik', obj.tahun_akademik)
        obj.updated_by = request.user.username
        obj.save()
        messages.success(request, 'Data pengabdian berhasil diupdate.')
    return redirect('pengabdian:index')


@login_required
def hapus_pengabdian(request, id):
    obj = get_object_or_404(Pengabdian, id=id)
    if not request.user.dapat_kelola(obj.user):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('pengabdian:index')
    obj.delete()
    messages.success(request, 'Data pengabdian berhasil dihapus.')
    return redirect('pengabdian:index')


@login_required
def kelola_anggota_pengabdian(request, pengabdian_id):
    pengabdian = get_object_or_404(Pengabdian, id=pengabdian_id)
    user = request.user
    bisa_edit = user.dapat_kelola(pengabdian.user) and cek_status_input()

    if not user.dapat_kelola(pengabdian.user):
        dosen = get_simda_dosen_or_none(user)
        is_co = dosen and pengabdian.anggota_set.filter(jenis_anggota='dosen', dosen_id=dosen.id).exists()
        if not is_co:
            messages.error(request, 'Tidak memiliki akses.')
            return redirect('pengabdian:index')

    if request.method == 'POST':
        aksi = request.POST.get('aksi')

        if aksi == 'tambah':
            if not bisa_edit:
                messages.error(request, 'Input data sedang dikunci.')
                return redirect('pengabdian:kelola_anggota_pengabdian', pengabdian_id=pengabdian_id)

            jenis_anggota = request.POST.get('jenis_anggota', '')
            anggota = AnggotaPengabdian(
                pengabdian=pengabdian,
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
                    return redirect('pengabdian:kelola_anggota_pengabdian', pengabdian_id=pengabdian_id)
                anggota.dosen_id = dosen.id
                anggota.nama = dosen.nama_lengkap_gelar
                anggota.nidn_nim = dosen.nidn
                anggota.perguruan_tinggi = 'Universitas Ichsan Gorontalo'
            elif jenis_anggota == 'mahasiswa':
                mhs_id = request.POST.get('mahasiswa_id')
                mhs = get_object_or_404(MahasiswaPublik.objects.using('simda'), id=mhs_id) if mhs_id else None
                if not mhs:
                    messages.error(request, 'Nama mahasiswa wajib dipilih.')
                    return redirect('pengabdian:kelola_anggota_pengabdian', pengabdian_id=pengabdian_id)
                anggota.mahasiswa_id = mhs.id
                anggota.nama = mhs.nama_lengkap
                anggota.nidn_nim = mhs.nim
            else:
                nama = request.POST.get('nama', '').strip()
                if not nama:
                    messages.error(request, 'Nama kolaborator wajib diisi.')
                    return redirect('pengabdian:kelola_anggota_pengabdian', pengabdian_id=pengabdian_id)
                anggota.nama = nama
                anggota.perguruan_tinggi = request.POST.get('perguruan_tinggi_lain', '').strip()

            anggota.save()
            messages.success(request, f'Anggota "{anggota.nama}" berhasil ditambahkan.')

        elif aksi == 'edit':
            if not bisa_edit:
                messages.error(request, 'Input data sedang dikunci.')
                return redirect('pengabdian:kelola_anggota_pengabdian', pengabdian_id=pengabdian_id)
            anggota = get_object_or_404(AnggotaPengabdian, id=request.POST.get('anggota_id'), pengabdian=pengabdian)
            anggota.peran = request.POST.get('peran', anggota.peran)
            anggota.status_aktif = bool(request.POST.get('status_aktif'))
            if anggota.jenis_anggota == 'kolaborator_eksternal':
                anggota.nama = request.POST.get('nama', '').strip() or anggota.nama
                anggota.perguruan_tinggi = request.POST.get('perguruan_tinggi_lain', '').strip()
            anggota.updated_by = user.username
            anggota.save()
            messages.success(request, 'Data anggota berhasil diupdate.')

        elif aksi == 'hapus':
            anggota = get_object_or_404(AnggotaPengabdian, id=request.POST.get('anggota_id'), pengabdian=pengabdian)
            if bisa_edit:
                nama = anggota.nama
                anggota.delete()
                messages.success(request, f'Anggota "{nama}" berhasil dihapus.')
            else:
                messages.error(request, 'Tidak memiliki akses.')

        return redirect('pengabdian:kelola_anggota_pengabdian', pengabdian_id=pengabdian_id)

    context = {
        'pengabdian': pengabdian,
        'bisa_edit': bisa_edit,
        'anggota_list': pengabdian.anggota_set.all(),
    }
    return render(request, 'pengabdian/kelola_anggota_pengabdian.html', context)


# ============================================================
# PEMBICARA
# ============================================================

@login_required
def tambah_pembicara(request):
    if request.method != 'POST':
        return redirect('pengabdian:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('pengabdian:index')

    target_user = _target_user(request, from_post=True)
    Pembicara.objects.create(
        user=target_user,
        kode_prodi=target_user.kode_prodi or '',
        kode_fakultas=target_user.kode_fakultas or '',
        kategori_kegiatan=request.POST.get('kategori_kegiatan', ''),
        kategori_capaian_luaran=request.POST.get('kategori_capaian_luaran', '').strip(),
        litabmas=request.POST.get('litabmas', '').strip(),
        kategori_pembicara=request.POST.get('kategori_pembicara', '').strip(),
        judul_makalah=request.POST.get('judul_makalah', '').strip(),
        nama_pertemuan_ilmiah=request.POST.get('nama_pertemuan_ilmiah', '').strip(),
        tingkat_pertemuan=request.POST.get('tingkat_pertemuan', '').strip(),
        penyelenggara=request.POST.get('penyelenggara', '').strip(),
        tanggal_pelaksanaan=request.POST.get('tanggal_pelaksanaan') or None,
        bahasa=request.POST.get('bahasa', '').strip(),
        no_sk_penugasan=request.POST.get('no_sk_penugasan', '').strip(),
        tanggal_sk_penugasan=request.POST.get('tanggal_sk_penugasan') or None,
        semester=request.POST.get('semester', ''),
        tahun_akademik=request.POST.get('tahun_akademik', ''),
        updated_by=request.user.username,
    )
    messages.success(request, 'Data pembicara berhasil ditambahkan.')
    return redirect('pengabdian:index')


@login_required
def edit_pembicara(request, id):
    obj = get_object_or_404(Pembicara, id=id)
    if not request.user.dapat_kelola(obj.user):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('pengabdian:index')
    if request.method == 'POST':
        obj.kategori_kegiatan = request.POST.get('kategori_kegiatan', obj.kategori_kegiatan)
        obj.kategori_capaian_luaran = request.POST.get('kategori_capaian_luaran', '').strip()
        obj.litabmas = request.POST.get('litabmas', '').strip()
        obj.kategori_pembicara = request.POST.get('kategori_pembicara', '').strip()
        obj.judul_makalah = request.POST.get('judul_makalah', '').strip()
        obj.nama_pertemuan_ilmiah = request.POST.get('nama_pertemuan_ilmiah', '').strip()
        obj.tingkat_pertemuan = request.POST.get('tingkat_pertemuan', '').strip()
        obj.penyelenggara = request.POST.get('penyelenggara', '').strip()
        obj.tanggal_pelaksanaan = request.POST.get('tanggal_pelaksanaan') or obj.tanggal_pelaksanaan
        obj.bahasa = request.POST.get('bahasa', '').strip()
        obj.no_sk_penugasan = request.POST.get('no_sk_penugasan', '').strip()
        obj.tanggal_sk_penugasan = request.POST.get('tanggal_sk_penugasan') or None
        obj.semester = request.POST.get('semester', '')
        obj.tahun_akademik = request.POST.get('tahun_akademik', obj.tahun_akademik)
        obj.updated_by = request.user.username
        obj.save()
        messages.success(request, 'Data pembicara berhasil diupdate.')
    return redirect('pengabdian:index')


@login_required
def hapus_pembicara(request, id):
    obj = get_object_or_404(Pembicara, id=id)
    if not request.user.dapat_kelola(obj.user):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('pengabdian:index')
    obj.delete()
    messages.success(request, 'Data pembicara berhasil dihapus.')
    return redirect('pengabdian:index')


# ============================================================
# PENGELOLA JURNAL
# ============================================================

@login_required
def tambah_jurnal(request):
    if request.method != 'POST':
        return redirect('pengabdian:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('pengabdian:index')

    target_user = _target_user(request, from_post=True)
    PengelolaJurnal.objects.create(
        user=target_user,
        kode_prodi=target_user.kode_prodi or '',
        kode_fakultas=target_user.kode_fakultas or '',
        nama_jurnal=request.POST.get('nama_jurnal', '').strip(),
        media_publikasi=request.POST.get('media_publikasi', '').strip(),
        peran=request.POST.get('peran', '').strip(),
        no_sk_penugasan=request.POST.get('no_sk_penugasan', '').strip(),
        terhitung_mulai_tanggal=request.POST.get('terhitung_mulai_tanggal') or None,
        tanggal_selesai=request.POST.get('tanggal_selesai') or None,
        status_aktif=(request.POST.get('status_aktif') == 'aktif'),
        semester=request.POST.get('semester', ''),
        tahun_akademik=request.POST.get('tahun_akademik', ''),
        updated_by=request.user.username,
    )
    messages.success(request, 'Data pengelola jurnal berhasil ditambahkan.')
    return redirect('pengabdian:index')


@login_required
def edit_jurnal(request, id):
    obj = get_object_or_404(PengelolaJurnal, id=id)
    if not request.user.dapat_kelola(obj.user):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('pengabdian:index')
    if request.method == 'POST':
        obj.nama_jurnal = request.POST.get('nama_jurnal', '').strip()
        obj.media_publikasi = request.POST.get('media_publikasi', '').strip()
        obj.peran = request.POST.get('peran', '').strip()
        obj.no_sk_penugasan = request.POST.get('no_sk_penugasan', '').strip()
        obj.terhitung_mulai_tanggal = request.POST.get('terhitung_mulai_tanggal') or obj.terhitung_mulai_tanggal
        obj.tanggal_selesai = request.POST.get('tanggal_selesai') or None
        obj.status_aktif = (request.POST.get('status_aktif') == 'aktif')
        obj.semester = request.POST.get('semester', '')
        obj.tahun_akademik = request.POST.get('tahun_akademik', obj.tahun_akademik)
        obj.updated_by = request.user.username
        obj.save()
        messages.success(request, 'Data pengelola jurnal berhasil diupdate.')
    return redirect('pengabdian:index')


@login_required
def hapus_jurnal(request, id):
    obj = get_object_or_404(PengelolaJurnal, id=id)
    if not request.user.dapat_kelola(obj.user):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('pengabdian:index')
    obj.delete()
    messages.success(request, 'Data pengelola jurnal berhasil dihapus.')
    return redirect('pengabdian:index')


# ============================================================
# JABATAN STRUKTURAL
# ============================================================

@login_required
def tambah_jabatan(request):
    if request.method != 'POST':
        return redirect('pengabdian:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('pengabdian:index')

    target_user = _target_user(request, from_post=True)
    JabatanStruktural.objects.create(
        user=target_user,
        kode_prodi=target_user.kode_prodi or '',
        kode_fakultas=target_user.kode_fakultas or '',
        jabatan_tugas=request.POST.get('jabatan_tugas', '').strip(),
        no_sk_jabatan_struktural=request.POST.get('no_sk_jabatan_struktural', '').strip(),
        terhitung_mulai_tanggal=request.POST.get('terhitung_mulai_tanggal') or None,
        terhitung_selesai_tanggal=request.POST.get('terhitung_selesai_tanggal') or None,
        lokasi_penugasan=request.POST.get('lokasi_penugasan', '').strip(),
        semester=request.POST.get('semester', ''),
        tahun_akademik=request.POST.get('tahun_akademik', ''),
        updated_by=request.user.username,
    )
    messages.success(request, 'Data jabatan struktural berhasil ditambahkan.')
    return redirect('pengabdian:index')


@login_required
def edit_jabatan(request, id):
    obj = get_object_or_404(JabatanStruktural, id=id)
    if not request.user.dapat_kelola(obj.user):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('pengabdian:index')
    if request.method == 'POST':
        obj.jabatan_tugas = request.POST.get('jabatan_tugas', '').strip()
        obj.no_sk_jabatan_struktural = request.POST.get('no_sk_jabatan_struktural', '').strip()
        obj.terhitung_mulai_tanggal = request.POST.get('terhitung_mulai_tanggal') or obj.terhitung_mulai_tanggal
        obj.terhitung_selesai_tanggal = request.POST.get('terhitung_selesai_tanggal') or None
        obj.lokasi_penugasan = request.POST.get('lokasi_penugasan', '').strip()
        obj.semester = request.POST.get('semester', '')
        obj.tahun_akademik = request.POST.get('tahun_akademik', obj.tahun_akademik)
        obj.updated_by = request.user.username
        obj.save()
        messages.success(request, 'Data jabatan struktural berhasil diupdate.')
    return redirect('pengabdian:index')


@login_required
def hapus_jabatan(request, id):
    obj = get_object_or_404(JabatanStruktural, id=id)
    if not request.user.dapat_kelola(obj.user):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('pengabdian:index')
    obj.delete()
    messages.success(request, 'Data jabatan struktural berhasil dihapus.')
    return redirect('pengabdian:index')
