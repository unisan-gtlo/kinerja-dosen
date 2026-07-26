from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from master.models import Pengaturan
from accounts.models import User
from kinerja.utils import attach_dokumen_count
from .models import Beasiswa, Kesejahteraan, Tunjangan

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


@login_required
def index(request):
    user = request.user
    target_user = _target_user(request)

    input_terbuka = cek_status_input()
    bisa_edit = user.dapat_kelola(target_user) and input_terbuka

    try:
        per_page = int(request.GET.get('per_page', DEFAULT_PER_PAGE))
    except (TypeError, ValueError):
        per_page = DEFAULT_PER_PAGE
    if per_page not in PER_PAGE_CHOICES:
        per_page = DEFAULT_PER_PAGE

    beasiswa_qs = Beasiswa.objects.filter(user=target_user)
    kesejahteraan_qs = Kesejahteraan.objects.filter(user=target_user)
    tunjangan_qs = Tunjangan.objects.filter(user=target_user)

    beasiswa_page = _paginate(request, beasiswa_qs, 'page_bea', per_page)
    kesejahteraan_page = _paginate(request, kesejahteraan_qs, 'page_kes', per_page)
    tunjangan_page = _paginate(request, tunjangan_qs, 'page_tun', per_page)

    attach_dokumen_count(beasiswa_page.object_list, 'beasiswa')
    attach_dokumen_count(kesejahteraan_page.object_list, 'kesejahteraan')
    attach_dokumen_count(tunjangan_page.object_list, 'tunjangan')

    context = {
        'target_user': target_user,
        'bisa_edit': bisa_edit,
        'input_terbuka': input_terbuka,
        'per_page': per_page,
        'per_page_choices': PER_PAGE_CHOICES,
        'beasiswa_list': beasiswa_page,
        'kesejahteraan_list': kesejahteraan_page,
        'tunjangan_list': tunjangan_page,
    }
    return render(request, 'reward/index.html', context)


# ============================================================
# BEASISWA
# ============================================================

@login_required
def tambah_beasiswa(request):
    if request.method != 'POST':
        return redirect('reward:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('reward:index')

    target_user = _target_user(request, from_post=True)
    Beasiswa.objects.create(
        user=target_user,
        kode_prodi=target_user.kode_prodi or '',
        kode_fakultas=target_user.kode_fakultas or '',
        jenis_beasiswa=request.POST.get('jenis_beasiswa', ''),
        nama_beasiswa=request.POST.get('nama_beasiswa', '').strip(),
        tahun_mulai=request.POST.get('tahun_mulai') or None,
        tahun_selesai=request.POST.get('tahun_selesai') or None,
        masih_terima=(request.POST.get('masih_terima') == 'ya'),
        updated_by=request.user.username,
    )
    messages.success(request, 'Data beasiswa berhasil ditambahkan.')
    return redirect('reward:index')


@login_required
def edit_beasiswa(request, id):
    obj = get_object_or_404(Beasiswa, id=id)
    if not request.user.dapat_kelola(obj.user):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('reward:index')
    if request.method == 'POST':
        obj.jenis_beasiswa = request.POST.get('jenis_beasiswa', obj.jenis_beasiswa)
        obj.nama_beasiswa = request.POST.get('nama_beasiswa', '').strip()
        obj.tahun_mulai = request.POST.get('tahun_mulai') or obj.tahun_mulai
        obj.tahun_selesai = request.POST.get('tahun_selesai') or None
        obj.masih_terima = (request.POST.get('masih_terima') == 'ya')
        obj.updated_by = request.user.username
        obj.save()
        messages.success(request, 'Data beasiswa berhasil diupdate.')
    return redirect('reward:index')


@login_required
def hapus_beasiswa(request, id):
    obj = get_object_or_404(Beasiswa, id=id)
    if not request.user.dapat_kelola(obj.user):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('reward:index')
    obj.delete()
    messages.success(request, 'Data beasiswa berhasil dihapus.')
    return redirect('reward:index')


# ============================================================
# KESEJAHTERAAN
# ============================================================

@login_required
def tambah_kesejahteraan(request):
    if request.method != 'POST':
        return redirect('reward:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('reward:index')

    target_user = _target_user(request, from_post=True)
    Kesejahteraan.objects.create(
        user=target_user,
        kode_prodi=target_user.kode_prodi or '',
        kode_fakultas=target_user.kode_fakultas or '',
        jenis_kesejahteraan=request.POST.get('jenis_kesejahteraan', ''),
        layanan_kesejahteraan=request.POST.get('layanan_kesejahteraan', '').strip(),
        penyelenggara=request.POST.get('penyelenggara', '').strip(),
        tahun_mulai=request.POST.get('tahun_mulai') or None,
        tahun_selesai=request.POST.get('tahun_selesai') or None,
        updated_by=request.user.username,
    )
    messages.success(request, 'Data kesejahteraan berhasil ditambahkan.')
    return redirect('reward:index')


@login_required
def edit_kesejahteraan(request, id):
    obj = get_object_or_404(Kesejahteraan, id=id)
    if not request.user.dapat_kelola(obj.user):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('reward:index')
    if request.method == 'POST':
        obj.jenis_kesejahteraan = request.POST.get('jenis_kesejahteraan', obj.jenis_kesejahteraan)
        obj.layanan_kesejahteraan = request.POST.get('layanan_kesejahteraan', '').strip()
        obj.penyelenggara = request.POST.get('penyelenggara', '').strip()
        obj.tahun_mulai = request.POST.get('tahun_mulai') or obj.tahun_mulai
        obj.tahun_selesai = request.POST.get('tahun_selesai') or None
        obj.updated_by = request.user.username
        obj.save()
        messages.success(request, 'Data kesejahteraan berhasil diupdate.')
    return redirect('reward:index')


@login_required
def hapus_kesejahteraan(request, id):
    obj = get_object_or_404(Kesejahteraan, id=id)
    if not request.user.dapat_kelola(obj.user):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('reward:index')
    obj.delete()
    messages.success(request, 'Data kesejahteraan berhasil dihapus.')
    return redirect('reward:index')


# ============================================================
# TUNJANGAN
# ============================================================

@login_required
def tambah_tunjangan(request):
    if request.method != 'POST':
        return redirect('reward:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('reward:index')

    target_user = _target_user(request, from_post=True)
    Tunjangan.objects.create(
        user=target_user,
        kode_prodi=target_user.kode_prodi or '',
        kode_fakultas=target_user.kode_fakultas or '',
        jenis_tunjangan=request.POST.get('jenis_tunjangan', ''),
        nama_tunjangan=request.POST.get('nama_tunjangan', '').strip(),
        instansi_pemberi_tunjangan=request.POST.get('instansi_pemberi_tunjangan', '').strip(),
        sumber_dana=request.POST.get('sumber_dana', '').strip(),
        tahun_mulai=request.POST.get('tahun_mulai') or None,
        tahun_selesai=request.POST.get('tahun_selesai') or None,
        nominal=request.POST.get('nominal') or 0,
        updated_by=request.user.username,
    )
    messages.success(request, 'Data tunjangan berhasil ditambahkan.')
    return redirect('reward:index')


@login_required
def edit_tunjangan(request, id):
    obj = get_object_or_404(Tunjangan, id=id)
    if not request.user.dapat_kelola(obj.user):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('reward:index')
    if request.method == 'POST':
        obj.jenis_tunjangan = request.POST.get('jenis_tunjangan', obj.jenis_tunjangan)
        obj.nama_tunjangan = request.POST.get('nama_tunjangan', '').strip()
        obj.instansi_pemberi_tunjangan = request.POST.get('instansi_pemberi_tunjangan', '').strip()
        obj.sumber_dana = request.POST.get('sumber_dana', '').strip()
        obj.tahun_mulai = request.POST.get('tahun_mulai') or obj.tahun_mulai
        obj.tahun_selesai = request.POST.get('tahun_selesai') or None
        obj.nominal = request.POST.get('nominal') or 0
        obj.updated_by = request.user.username
        obj.save()
        messages.success(request, 'Data tunjangan berhasil diupdate.')
    return redirect('reward:index')


@login_required
def hapus_tunjangan(request, id):
    obj = get_object_or_404(Tunjangan, id=id)
    if not request.user.dapat_kelola(obj.user):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('reward:index')
    obj.delete()
    messages.success(request, 'Data tunjangan berhasil dihapus.')
    return redirect('reward:index')
