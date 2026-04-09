from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Fakultas, Prodi, TahunAkademik, Pengaturan

@login_required
def index(request):
    if request.user.role != 'admin':
        messages.error(request, 'Anda tidak memiliki akses.')
        return redirect('dashboard:index')
    fakultas_list = Fakultas.objects.all().order_by('kode_fakultas')
    prodi_list = Prodi.objects.all().order_by('fakultas__kode_fakultas', 'kode_prodi')
    tahun_list = TahunAkademik.objects.all().order_by('-urutan')
    try:
        pengaturan = Pengaturan.objects.first()
    except:
        pengaturan = None
    context = {
        'fakultas_list': fakultas_list,
        'prodi_list': prodi_list,
        'tahun_list': tahun_list,
        'pengaturan': pengaturan,
    }
    return render(request, 'master/index.html', context)

@login_required
def simpan_fakultas(request):
    if request.user.role != 'admin':
        return redirect('dashboard:index')
    if request.method == 'POST':
        aksi = request.POST.get('aksi')
        if aksi == 'tambah':
            kode = request.POST.get('kode_fakultas', '').strip().upper()
            nama = request.POST.get('nama_fakultas', '').strip()
            dekan = request.POST.get('nama_dekan', '').strip()
            if not kode or not nama:
                messages.error(request, 'Kode dan nama fakultas wajib diisi.')
            elif Fakultas.objects.filter(kode_fakultas=kode).exists():
                messages.error(request, f'Kode "{kode}" sudah digunakan.')
            else:
                Fakultas.objects.create(kode_fakultas=kode, nama_fakultas=nama, nama_dekan=dekan)
                messages.success(request, f'Fakultas "{nama}" berhasil ditambahkan.')
        elif aksi == 'edit':
            fak_id = request.POST.get('fak_id')
            fak = get_object_or_404(Fakultas, id=fak_id)
            fak.nama_fakultas = request.POST.get('nama_fakultas', '').strip()
            fak.nama_dekan = request.POST.get('nama_dekan', '').strip()
            fak.status = request.POST.get('status', 'aktif')
            fak.save()
            messages.success(request, 'Fakultas berhasil diupdate.')
        elif aksi == 'hapus':
            fak_id = request.POST.get('fak_id')
            fak = get_object_or_404(Fakultas, id=fak_id)
            fak.delete()
            messages.success(request, 'Fakultas berhasil dihapus.')
    return redirect('master:index')

@login_required
def simpan_prodi(request):
    if request.user.role != 'admin':
        return redirect('dashboard:index')
    if request.method == 'POST':
        aksi = request.POST.get('aksi')
        if aksi == 'tambah':
            kode = request.POST.get('kode_prodi', '').strip().upper()
            nama = request.POST.get('nama_prodi', '').strip()
            fak_id = request.POST.get('fakultas_id')
            jenjang = request.POST.get('jenjang', 'S1')
            kaprodi = request.POST.get('nama_kaprodi', '').strip()
            if not kode or not nama or not fak_id:
                messages.error(request, 'Kode, nama, dan fakultas wajib diisi.')
            elif Prodi.objects.filter(kode_prodi=kode).exists():
                messages.error(request, f'Kode "{kode}" sudah digunakan.')
            else:
                fak = get_object_or_404(Fakultas, id=fak_id)
                Prodi.objects.create(
                    kode_prodi=kode, nama_prodi=nama,
                    fakultas=fak, jenjang=jenjang, nama_kaprodi=kaprodi
                )
                messages.success(request, f'Prodi "{nama}" berhasil ditambahkan.')
        elif aksi == 'edit':
            prodi_id = request.POST.get('prodi_id')
            prodi = get_object_or_404(Prodi, id=prodi_id)
            prodi.nama_prodi = request.POST.get('nama_prodi', '').strip()
            prodi.nama_kaprodi = request.POST.get('nama_kaprodi', '').strip()
            prodi.jenjang = request.POST.get('jenjang', 'S1')
            prodi.status = request.POST.get('status', 'aktif')
            fak_id = request.POST.get('fakultas_id')
            if fak_id:
                prodi.fakultas = get_object_or_404(Fakultas, id=fak_id)
            prodi.save()
            messages.success(request, 'Prodi berhasil diupdate.')
        elif aksi == 'hapus':
            prodi_id = request.POST.get('prodi_id')
            prodi = get_object_or_404(Prodi, id=prodi_id)
            prodi.delete()
            messages.success(request, 'Prodi berhasil dihapus.')
    return redirect('master:index')

@login_required
def simpan_tahun(request):
    if request.user.role != 'admin':
        return redirect('dashboard:index')
    if request.method == 'POST':
        aksi = request.POST.get('aksi')
        if aksi == 'tambah':
            tahun = request.POST.get('tahun_akademik', '').strip()
            ket = request.POST.get('keterangan', '').strip()
            urutan = request.POST.get('urutan', 0)
            status = request.POST.get('status', 'aktif')
            if not tahun:
                messages.error(request, 'Tahun akademik wajib diisi.')
            elif TahunAkademik.objects.filter(tahun_akademik=tahun).exists():
                messages.error(request, f'Tahun "{tahun}" sudah ada.')
            else:
                TahunAkademik.objects.create(
                    tahun_akademik=tahun, keterangan=ket,
                    urutan=urutan, status=status
                )
                messages.success(request, f'Tahun akademik "{tahun}" berhasil ditambahkan.')
        elif aksi == 'edit':
            tahun_id = request.POST.get('tahun_id')
            ta = get_object_or_404(TahunAkademik, id=tahun_id)
            ta.keterangan = request.POST.get('keterangan', '').strip()
            ta.urutan = request.POST.get('urutan', 0)
            ta.status = request.POST.get('status', 'aktif')
            ta.save()
            messages.success(request, 'Tahun akademik berhasil diupdate.')
        elif aksi == 'hapus':
            tahun_id = request.POST.get('tahun_id')
            ta = get_object_or_404(TahunAkademik, id=tahun_id)
            ta.delete()
            messages.success(request, 'Tahun akademik berhasil dihapus.')
    return redirect('master:index')

@login_required
def simpan_pengaturan(request):
    if request.user.role != 'admin':
        return redirect('dashboard:index')
    if request.method == 'POST':
        pengaturan = Pengaturan.objects.first()
        if not pengaturan:
            pengaturan = Pengaturan()
        pengaturan.status_input = request.POST.get('status_input', 'buka')
        pengaturan.deadline = request.POST.get('deadline') or None
        pengaturan.ts_label = request.POST.get('ts_label', 'TS')
        pengaturan.ts_tahun = request.POST.get('ts_tahun', '')
        pengaturan.ts1_label = request.POST.get('ts1_label', 'TS-1')
        pengaturan.ts1_tahun = request.POST.get('ts1_tahun', '')
        pengaturan.ts2_label = request.POST.get('ts2_label', 'TS-2')
        pengaturan.ts2_tahun = request.POST.get('ts2_tahun', '')
        pengaturan.save()
        messages.success(request, 'Pengaturan berhasil disimpan.')
    return redirect('master:index')