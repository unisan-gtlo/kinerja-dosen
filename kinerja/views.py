from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from master.models import TahunAkademik, Pengaturan
from accounts.models import User
from .models import BKD, Penelitian, Publikasi, PKM, HKI

def cek_status_input():
    try:
        p = Pengaturan.objects.first()
        return p.status_input == 'buka' if p else True
    except:
        return True

@login_required
def index(request):
    user = request.user
    target_user = user

    dosen_id = request.GET.get('dosen_id')
    if dosen_id and user.role in ['admin', 'kaprodi', 'sekprodi', 'operator', 'dekan', 'wadek', 'rektorat', 'biro']:
        target_user = get_object_or_404(User, id=dosen_id)

    tahun_list = TahunAkademik.objects.filter(status='aktif').order_by('-urutan')
    input_terbuka = cek_status_input()
    bisa_edit = (user == target_user or user.role in ['admin', 'operator']) and input_terbuka

    # Filter
    filter_tahun = request.GET.get('tahun', '')
    filter_semester = request.GET.get('semester', '')

    bkd_list = target_user.bkd_set.all()
    penelitian_list = target_user.penelitian_set.all()
    publikasi_list = target_user.publikasi_set.all()
    pkm_list = target_user.pkm_set.all()
    hki_list = target_user.hki_set.all()

    if filter_tahun:
        bkd_list = bkd_list.filter(tahun_akademik=filter_tahun)
        penelitian_list = penelitian_list.filter(tahun_akademik=filter_tahun)
        publikasi_list = publikasi_list.filter(tahun_akademik=filter_tahun)
        pkm_list = pkm_list.filter(tahun_akademik=filter_tahun)
        hki_list = hki_list.filter(tahun_akademik=filter_tahun)

    if filter_semester:
        bkd_list = bkd_list.filter(semester=filter_semester)
        penelitian_list = penelitian_list.filter(semester=filter_semester)
        publikasi_list = publikasi_list.filter(semester=filter_semester)
        pkm_list = pkm_list.filter(semester=filter_semester)
        hki_list = hki_list.filter(semester=filter_semester)

    context = {
        'target_user': target_user,
        'tahun_list': tahun_list,
        'bisa_edit': bisa_edit,
        'input_terbuka': input_terbuka,
        'filter_tahun': filter_tahun,
        'filter_semester': filter_semester,
        'bkd_list': bkd_list,
        'penelitian_list': penelitian_list,
        'publikasi_list': publikasi_list,
        'pkm_list': pkm_list,
        'hki_list': hki_list,
    }
    return render(request, 'kinerja/index.html', context)


@login_required
def tambah_bkd(request):
    if request.method != 'POST':
        return redirect('kinerja:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('kinerja:index')

    user = request.user
    dosen_id = request.POST.get('dosen_id')
    target_user = get_object_or_404(User, id=dosen_id) if dosen_id and user.role in ['admin', 'operator'] else user

    semester = request.POST.get('semester', '')
    tahun_akademik = request.POST.get('tahun_akademik', '')

    if BKD.objects.filter(user=target_user, semester=semester, tahun_akademik=tahun_akademik).exists():
        messages.error(request, f'BKD {semester} {tahun_akademik} sudah ada.')
        return redirect('kinerja:index')

    bkd = BKD(
        user=target_user,
        kode_prodi=target_user.kode_prodi,
        kode_fakultas=target_user.kode_fakultas,
        semester=semester,
        tahun_akademik=tahun_akademik,
        link_bkd=request.POST.get('link_bkd', '').strip(),
        keterangan=request.POST.get('keterangan', '').strip(),
        updated_by=user.username
    )
    if 'file_bkd' in request.FILES:
        bkd.file_bkd = request.FILES['file_bkd']
    bkd.save()
    messages.success(request, f'BKD {semester} {tahun_akademik} berhasil disimpan.')
    return redirect('kinerja:index')


@login_required
def hapus_bkd(request, bkd_id):
    bkd = get_object_or_404(BKD, id=bkd_id)
    if request.user != bkd.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('kinerja:index')
    bkd.delete()
    messages.success(request, 'BKD berhasil dihapus.')
    return redirect('kinerja:index')


@login_required
def tambah_penelitian(request):
    if request.method != 'POST':
        return redirect('kinerja:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('kinerja:index')

    user = request.user
    dosen_id = request.POST.get('dosen_id')
    target_user = get_object_or_404(User, id=dosen_id) if dosen_id and user.role in ['admin', 'operator'] else user

    Penelitian.objects.create(
        user=target_user,
        kode_prodi=target_user.kode_prodi or '',
        kode_fakultas=target_user.kode_fakultas or '',
        judul=request.POST.get('judul', '').strip(),
        jml_mahasiswa=request.POST.get('jml_mahasiswa', 0),
        jenis_hibah=request.POST.get('jenis_hibah', '').strip(),
        sumber=request.POST.get('sumber', '').strip(),
        durasi=request.POST.get('durasi', 1),
        ln_i=request.POST.get('ln_i', ''),
        semester=request.POST.get('semester', ''),
        tahun_akademik=request.POST.get('tahun_akademik', ''),
        pendanaan=request.POST.get('pendanaan', 0) or 0,
        link_bukti=request.POST.get('link_bukti', '').strip(),
        updated_by=user.username
    )
    messages.success(request, 'Data penelitian berhasil ditambahkan.')
    return redirect('kinerja:index')


@login_required
def hapus_penelitian(request, id):
    obj = get_object_or_404(Penelitian, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('kinerja:index')
    obj.delete()
    messages.success(request, 'Data penelitian berhasil dihapus.')
    return redirect('kinerja:index')


@login_required
def tambah_publikasi(request):
    if request.method != 'POST':
        return redirect('kinerja:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('kinerja:index')

    user = request.user
    dosen_id = request.POST.get('dosen_id')
    target_user = get_object_or_404(User, id=dosen_id) if dosen_id and user.role in ['admin', 'operator'] else user

    Publikasi.objects.create(
        user=target_user,
        kode_prodi=target_user.kode_prodi or '',
        kode_fakultas=target_user.kode_fakultas or '',
        judul=request.POST.get('judul', '').strip(),
        jenis_publikasi=request.POST.get('jenis_publikasi', ''),
        nama_jurnal=request.POST.get('nama_jurnal', '').strip(),
        volume=request.POST.get('volume', '').strip(),
        nomor=request.POST.get('nomor', '').strip(),
        halaman=request.POST.get('halaman', '').strip(),
        tahun_terbit=request.POST.get('tahun_terbit') or None,
        semester=request.POST.get('semester', ''),
        tahun_akademik=request.POST.get('tahun_akademik', ''),
        link_bukti=request.POST.get('link_bukti', '').strip(),
        updated_by=user.username
    )
    messages.success(request, 'Data publikasi berhasil ditambahkan.')
    return redirect('kinerja:index')


@login_required
def hapus_publikasi(request, id):
    obj = get_object_or_404(Publikasi, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('kinerja:index')
    obj.delete()
    messages.success(request, 'Data publikasi berhasil dihapus.')
    return redirect('kinerja:index')


@login_required
def tambah_pkm(request):
    if request.method != 'POST':
        return redirect('kinerja:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('kinerja:index')

    user = request.user
    dosen_id = request.POST.get('dosen_id')
    target_user = get_object_or_404(User, id=dosen_id) if dosen_id and user.role in ['admin', 'operator'] else user

    PKM.objects.create(
        user=target_user,
        kode_prodi=target_user.kode_prodi or '',
        kode_fakultas=target_user.kode_fakultas or '',
        judul=request.POST.get('judul', '').strip(),
        jml_mahasiswa=request.POST.get('jml_mahasiswa', 0),
        jenis_hibah=request.POST.get('jenis_hibah', '').strip(),
        sumber=request.POST.get('sumber', '').strip(),
        durasi=request.POST.get('durasi', 1),
        ln_i=request.POST.get('ln_i', ''),
        semester=request.POST.get('semester', ''),
        tahun_akademik=request.POST.get('tahun_akademik', ''),
        pendanaan=request.POST.get('pendanaan', 0) or 0,
        link_bukti=request.POST.get('link_bukti', '').strip(),
        updated_by=user.username
    )
    messages.success(request, 'Data PKM berhasil ditambahkan.')
    return redirect('kinerja:index')


@login_required
def hapus_pkm(request, id):
    obj = get_object_or_404(PKM, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('kinerja:index')
    obj.delete()
    messages.success(request, 'Data PKM berhasil dihapus.')
    return redirect('kinerja:index')


@login_required
def tambah_hki(request):
    if request.method != 'POST':
        return redirect('kinerja:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('kinerja:index')

    user = request.user
    dosen_id = request.POST.get('dosen_id')
    target_user = get_object_or_404(User, id=dosen_id) if dosen_id and user.role in ['admin', 'operator'] else user

    HKI.objects.create(
        user=target_user,
        kode_prodi=target_user.kode_prodi or '',
        kode_fakultas=target_user.kode_fakultas or '',
        judul=request.POST.get('judul', '').strip(),
        jenis_hki=request.POST.get('jenis_hki', ''),
        no_hki=request.POST.get('no_hki', '').strip(),
        tahun_perolehan=request.POST.get('tahun_perolehan') or None,
        semester=request.POST.get('semester', ''),
        tahun_akademik=request.POST.get('tahun_akademik', ''),
        link_bukti=request.POST.get('link_bukti', '').strip(),
        updated_by=user.username
    )
    messages.success(request, 'Data HKI berhasil ditambahkan.')
    return redirect('kinerja:index')


@login_required
def hapus_hki(request, id):
    obj = get_object_or_404(HKI, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('kinerja:index')
    obj.delete()
    messages.success(request, 'Data HKI berhasil dihapus.')
    return redirect('kinerja:index')