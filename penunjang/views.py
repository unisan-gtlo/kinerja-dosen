from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from master.models import TahunAkademik, Pengaturan
from accounts.models import User
from simda_dosen.models import DataDosen
from simda_dosen.utils import get_simda_dosen_or_none, bisa_tambah_tridarma, redirect_ke
from kinerja.utils import attach_dokumen_count
from .models import AnggotaProfesi, Penghargaan, PenunjangLain, AnggotaPenunjangLain

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


def _co_author_queryset_penunjang(target_user):
    """Record milik target_user sendiri, ditambah record dosen lain yang
    mencantumkan target_user sebagai Anggota Kegiatan (Dosen) -- sama pola
    dengan Penelitian/Pengabdian, tapi Anggota Penunjang Lain cuma dosen
    (tidak ada jenis_anggota) jadi filter-nya lebih sederhana."""
    qs = PenunjangLain.objects.filter(user=target_user)
    dosen = get_simda_dosen_or_none(target_user)
    if dosen:
        qs = qs | PenunjangLain.objects.filter(anggota_set__dosen_id=dosen.id)
    return qs.select_related('user').distinct()


def _attach_co_anggota(page_obj, target_user):
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
    bisa_tambah = bisa_tambah_tridarma(user, target_user) and input_terbuka

    try:
        per_page = int(request.GET.get('per_page', DEFAULT_PER_PAGE))
    except (TypeError, ValueError):
        per_page = DEFAULT_PER_PAGE
    if per_page not in PER_PAGE_CHOICES:
        per_page = DEFAULT_PER_PAGE

    profesi_qs = AnggotaProfesi.objects.filter(user=target_user)
    penghargaan_qs = Penghargaan.objects.filter(user=target_user)
    penunjang_qs = _co_author_queryset_penunjang(target_user)

    profesi_page = _paginate(request, profesi_qs, 'page_prof', per_page)
    penghargaan_page = _paginate(request, penghargaan_qs, 'page_pgh', per_page)
    penunjang_page = _paginate(request, penunjang_qs, 'page_pnj', per_page)

    _attach_co_anggota(penunjang_page, target_user)

    attach_dokumen_count(profesi_page.object_list, 'anggota_profesi')
    attach_dokumen_count(penghargaan_page.object_list, 'penghargaan')
    attach_dokumen_count(penunjang_page.object_list, 'penunjang')

    context = {
        'target_user': target_user,
        'tahun_list': tahun_list,
        'bisa_edit': bisa_edit,
        'bisa_tambah': bisa_tambah,
        'input_terbuka': input_terbuka,
        'per_page': per_page,
        'per_page_choices': PER_PAGE_CHOICES,
        'profesi_list': profesi_page,
        'penghargaan_list': penghargaan_page,
        'penunjang_list': penunjang_page,
    }
    return render(request, 'penunjang/index.html', context)


# ============================================================
# ANGGOTA PROFESI
# ============================================================

@login_required
def tambah_profesi(request):
    if request.method != 'POST':
        return redirect('penunjang:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('penunjang:index')

    target_user = _target_user(request, from_post=True)
    if not bisa_tambah_tridarma(request.user, target_user):
        messages.error(request, 'Hanya admin/operator yang bisa menambahkan data untuk dosen lain.')
        return redirect_ke('penunjang:index', request.user, target_user.id)
    AnggotaProfesi.objects.create(
        user=target_user,
        kode_prodi=target_user.kode_prodi or '',
        kode_fakultas=target_user.kode_fakultas or '',
        kategori_kegiatan=request.POST.get('kategori_kegiatan', ''),
        nama_organisasi=request.POST.get('nama_organisasi', '').strip(),
        peran=request.POST.get('peran', '').strip(),
        mulai_keanggotaan=request.POST.get('mulai_keanggotaan') or None,
        selesai_keanggotaan=request.POST.get('selesai_keanggotaan') or None,
        instansi_profesi=request.POST.get('instansi_profesi', '').strip(),
        semester=request.POST.get('semester', ''),
        tahun_akademik=request.POST.get('tahun_akademik', ''),
        updated_by=request.user.username,
    )
    messages.success(request, 'Data anggota profesi berhasil ditambahkan.')
    return redirect_ke('penunjang:index', request.user, target_user.id)


@login_required
def edit_profesi(request, id):
    obj = get_object_or_404(AnggotaProfesi, id=id)
    if not request.user.dapat_kelola(obj.user):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect_ke('penunjang:index', request.user, obj.user_id)
    if request.method == 'POST':
        obj.kategori_kegiatan = request.POST.get('kategori_kegiatan', obj.kategori_kegiatan)
        obj.nama_organisasi = request.POST.get('nama_organisasi', '').strip()
        obj.peran = request.POST.get('peran', '').strip()
        obj.mulai_keanggotaan = request.POST.get('mulai_keanggotaan') or obj.mulai_keanggotaan
        obj.selesai_keanggotaan = request.POST.get('selesai_keanggotaan') or None
        obj.instansi_profesi = request.POST.get('instansi_profesi', '').strip()
        obj.semester = request.POST.get('semester', '')
        obj.tahun_akademik = request.POST.get('tahun_akademik', obj.tahun_akademik)
        obj.updated_by = request.user.username
        obj.save()
        messages.success(request, 'Data anggota profesi berhasil diupdate.')
    return redirect_ke('penunjang:index', request.user, obj.user_id)


@login_required
def hapus_profesi(request, id):
    obj = get_object_or_404(AnggotaProfesi, id=id)
    if not request.user.dapat_kelola(obj.user):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect_ke('penunjang:index', request.user, obj.user_id)
    obj.delete()
    messages.success(request, 'Data anggota profesi berhasil dihapus.')
    return redirect_ke('penunjang:index', request.user, obj.user_id)


# ============================================================
# PENGHARGAAN
# ============================================================

@login_required
def tambah_penghargaan(request):
    if request.method != 'POST':
        return redirect('penunjang:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('penunjang:index')

    target_user = _target_user(request, from_post=True)
    if not bisa_tambah_tridarma(request.user, target_user):
        messages.error(request, 'Hanya admin/operator yang bisa menambahkan data untuk dosen lain.')
        return redirect_ke('penunjang:index', request.user, target_user.id)
    Penghargaan.objects.create(
        user=target_user,
        kode_prodi=target_user.kode_prodi or '',
        kode_fakultas=target_user.kode_fakultas or '',
        kategori_kegiatan=request.POST.get('kategori_kegiatan', ''),
        tingkat_penghargaan=request.POST.get('tingkat_penghargaan', ''),
        jenis_penghargaan=request.POST.get('jenis_penghargaan', '').strip(),
        nama_penghargaan=request.POST.get('nama_penghargaan', '').strip(),
        tahun=request.POST.get('tahun') or None,
        instansi_pemberi=request.POST.get('instansi_pemberi', '').strip(),
        semester=request.POST.get('semester', ''),
        tahun_akademik=request.POST.get('tahun_akademik', ''),
        updated_by=request.user.username,
    )
    messages.success(request, 'Data penghargaan berhasil ditambahkan.')
    return redirect_ke('penunjang:index', request.user, target_user.id)


@login_required
def edit_penghargaan(request, id):
    obj = get_object_or_404(Penghargaan, id=id)
    if not request.user.dapat_kelola(obj.user):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect_ke('penunjang:index', request.user, obj.user_id)
    if request.method == 'POST':
        obj.kategori_kegiatan = request.POST.get('kategori_kegiatan', obj.kategori_kegiatan)
        obj.tingkat_penghargaan = request.POST.get('tingkat_penghargaan', obj.tingkat_penghargaan)
        obj.jenis_penghargaan = request.POST.get('jenis_penghargaan', '').strip()
        obj.nama_penghargaan = request.POST.get('nama_penghargaan', '').strip()
        obj.tahun = request.POST.get('tahun') or obj.tahun
        obj.instansi_pemberi = request.POST.get('instansi_pemberi', '').strip()
        obj.semester = request.POST.get('semester', '')
        obj.tahun_akademik = request.POST.get('tahun_akademik', obj.tahun_akademik)
        obj.updated_by = request.user.username
        obj.save()
        messages.success(request, 'Data penghargaan berhasil diupdate.')
    return redirect_ke('penunjang:index', request.user, obj.user_id)


@login_required
def hapus_penghargaan(request, id):
    obj = get_object_or_404(Penghargaan, id=id)
    if not request.user.dapat_kelola(obj.user):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect_ke('penunjang:index', request.user, obj.user_id)
    obj.delete()
    messages.success(request, 'Data penghargaan berhasil dihapus.')
    return redirect_ke('penunjang:index', request.user, obj.user_id)


# ============================================================
# PENUNJANG LAIN
# ============================================================

@login_required
def tambah_penunjang(request):
    if request.method != 'POST':
        return redirect('penunjang:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('penunjang:index')

    target_user = _target_user(request, from_post=True)
    if not bisa_tambah_tridarma(request.user, target_user):
        messages.error(request, 'Hanya admin/operator yang bisa menambahkan data untuk dosen lain.')
        return redirect_ke('penunjang:index', request.user, target_user.id)
    PenunjangLain.objects.create(
        user=target_user,
        kode_prodi=target_user.kode_prodi or '',
        kode_fakultas=target_user.kode_fakultas or '',
        kategori_kegiatan=request.POST.get('kategori_kegiatan', '').strip(),
        nama_kegiatan=request.POST.get('nama_kegiatan', '').strip(),
        jenis_kegiatan=request.POST.get('jenis_kegiatan', ''),
        instansi=request.POST.get('instansi', '').strip(),
        tingkat=request.POST.get('tingkat', ''),
        no_sk_penugasan=request.POST.get('no_sk_penugasan', '').strip(),
        tanggal_mulai=request.POST.get('tanggal_mulai') or None,
        tanggal_selesai=request.POST.get('tanggal_selesai') or None,
        semester=request.POST.get('semester', ''),
        tahun_akademik=request.POST.get('tahun_akademik', ''),
        updated_by=request.user.username,
    )
    messages.success(request, 'Data penunjang lain berhasil ditambahkan.')
    return redirect_ke('penunjang:index', request.user, target_user.id)


@login_required
def edit_penunjang(request, id):
    obj = get_object_or_404(PenunjangLain, id=id)
    if not request.user.dapat_kelola(obj.user):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect_ke('penunjang:index', request.user, obj.user_id)
    if request.method == 'POST':
        obj.kategori_kegiatan = request.POST.get('kategori_kegiatan', '').strip()
        obj.nama_kegiatan = request.POST.get('nama_kegiatan', '').strip()
        obj.jenis_kegiatan = request.POST.get('jenis_kegiatan', obj.jenis_kegiatan)
        obj.instansi = request.POST.get('instansi', '').strip()
        obj.tingkat = request.POST.get('tingkat', obj.tingkat)
        obj.no_sk_penugasan = request.POST.get('no_sk_penugasan', '').strip()
        obj.tanggal_mulai = request.POST.get('tanggal_mulai') or obj.tanggal_mulai
        obj.tanggal_selesai = request.POST.get('tanggal_selesai') or None
        obj.semester = request.POST.get('semester', '')
        obj.tahun_akademik = request.POST.get('tahun_akademik', obj.tahun_akademik)
        obj.updated_by = request.user.username
        obj.save()
        messages.success(request, 'Data penunjang lain berhasil diupdate.')
    return redirect_ke('penunjang:index', request.user, obj.user_id)


@login_required
def hapus_penunjang(request, id):
    obj = get_object_or_404(PenunjangLain, id=id)
    if not request.user.dapat_kelola(obj.user):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect_ke('penunjang:index', request.user, obj.user_id)
    obj.delete()
    messages.success(request, 'Data penunjang lain berhasil dihapus.')
    return redirect_ke('penunjang:index', request.user, obj.user_id)


@login_required
def kelola_anggota_penunjang(request, penunjang_id):
    obj = get_object_or_404(PenunjangLain, id=penunjang_id)
    user = request.user
    bisa_edit = user.dapat_kelola(obj.user) and cek_status_input()

    if not user.dapat_kelola(obj.user):
        dosen = get_simda_dosen_or_none(user)
        is_co = dosen and obj.anggota_set.filter(dosen_id=dosen.id).exists()
        if not is_co:
            messages.error(request, 'Tidak memiliki akses.')
            return redirect_ke('penunjang:index', request.user, obj.user_id)

    if request.method == 'POST':
        aksi = request.POST.get('aksi')

        if aksi == 'tambah':
            if not bisa_edit:
                messages.error(request, 'Input data sedang dikunci.')
                return redirect('penunjang:kelola_anggota_penunjang', penunjang_id=penunjang_id)

            dosen_id = request.POST.get('dosen_id')
            dosen = get_object_or_404(DataDosen.objects.using('simda'), id=dosen_id) if dosen_id else None
            if not dosen:
                messages.error(request, 'Nama dosen wajib dipilih.')
                return redirect('penunjang:kelola_anggota_penunjang', penunjang_id=penunjang_id)

            anggota = AnggotaPenunjangLain.objects.create(
                penunjang_lain=obj,
                dosen_id=dosen.id,
                nama=dosen.nama_lengkap_gelar,
                nidn=dosen.nidn,
                perguruan_tinggi='Universitas Ichsan Gorontalo',
                peran=request.POST.get('peran', '').strip(),
                updated_by=user.username,
            )
            messages.success(request, f'Anggota "{anggota.nama}" berhasil ditambahkan.')

        elif aksi == 'edit':
            if not bisa_edit:
                messages.error(request, 'Input data sedang dikunci.')
                return redirect('penunjang:kelola_anggota_penunjang', penunjang_id=penunjang_id)
            anggota = get_object_or_404(AnggotaPenunjangLain, id=request.POST.get('anggota_id'), penunjang_lain=obj)
            anggota.peran = request.POST.get('peran', '').strip()
            anggota.updated_by = user.username
            anggota.save()
            messages.success(request, 'Data anggota berhasil diupdate.')

        elif aksi == 'hapus':
            anggota = get_object_or_404(AnggotaPenunjangLain, id=request.POST.get('anggota_id'), penunjang_lain=obj)
            if bisa_edit:
                nama = anggota.nama
                anggota.delete()
                messages.success(request, f'Anggota "{nama}" berhasil dihapus.')
            else:
                messages.error(request, 'Tidak memiliki akses.')

        return redirect('penunjang:kelola_anggota_penunjang', penunjang_id=penunjang_id)

    context = {
        'penunjang': obj,
        'bisa_edit': bisa_edit,
        'anggota_list': obj.anggota_set.all(),
    }
    return render(request, 'penunjang/kelola_anggota_penunjang.html', context)
