from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from accounts.models import User
from master.models import Fakultas, Prodi
from profil.models import ProfilDosen
from kinerja.models import Penelitian, Publikasi, PKM, HKI

@login_required
def index(request):
    user = request.user
    context = {}

    if user.role in ['admin', 'rektorat', 'biro']:
        context['total_dosen'] = User.objects.filter(role='dosen', status_akun='aktif').count()
        context['total_fakultas'] = Fakultas.objects.filter(status='aktif').count()
        context['total_prodi'] = Prodi.objects.filter(status='aktif').count()
        context['total_penelitian'] = Penelitian.objects.count()
        context['total_publikasi'] = Publikasi.objects.count()
        context['total_pkm'] = PKM.objects.count()
        context['total_hki'] = HKI.objects.count()
        context['dosen_list'] = User.objects.filter(
            role='dosen', status_akun='aktif'
        ).order_by('kode_fakultas', 'kode_prodi', 'first_name')[:10]

    elif user.role in ['dekan', 'wadek']:
        context['total_dosen'] = User.objects.filter(
            role='dosen', kode_fakultas=user.kode_fakultas, status_akun='aktif'
        ).count()
        context['total_prodi'] = Prodi.objects.filter(
            fakultas__kode_fakultas=user.kode_fakultas, status='aktif'
        ).count()
        context['total_penelitian'] = Penelitian.objects.filter(
            kode_fakultas=user.kode_fakultas
        ).count()
        context['total_publikasi'] = Publikasi.objects.filter(
            kode_fakultas=user.kode_fakultas
        ).count()

    elif user.role in ['kaprodi', 'sekprodi', 'operator']:
        context['total_dosen'] = User.objects.filter(
            role='dosen', kode_prodi=user.kode_prodi, status_akun='aktif'
        ).count()
        context['total_penelitian'] = Penelitian.objects.filter(
            kode_prodi=user.kode_prodi
        ).count()
        context['total_publikasi'] = Publikasi.objects.filter(
            kode_prodi=user.kode_prodi
        ).count()
        context['dosen_list'] = User.objects.filter(
            role='dosen', kode_prodi=user.kode_prodi, status_akun='aktif'
        ).order_by('first_name')

    elif user.role == 'dosen':
        try:
            profil = user.profil
            context['kelengkapan'] = profil.persentase_kelengkapan
        except:
            context['kelengkapan'] = 0
        context['total_penelitian'] = user.penelitian_set.count()
        context['total_publikasi'] = user.publikasi_set.count()
        context['total_pkm'] = user.pkm_set.count()
        context['total_hki'] = user.hki_set.count()
        context['total_bkd'] = user.bkd_set.count()

    return render(request, 'dashboard/index.html', context)

@login_required
def rekap(request):
    user = request.user
    context = {}

    if user.role in ['admin', 'rektorat', 'biro']:
        context['fakultas_list'] = Fakultas.objects.filter(status='aktif')
        context['dosen_list'] = User.objects.filter(
            role='dosen', status_akun='aktif'
        ).order_by('kode_fakultas', 'kode_prodi', 'first_name')

    elif user.role in ['dekan', 'wadek']:
        context['prodi_list'] = Prodi.objects.filter(
            fakultas__kode_fakultas=user.kode_fakultas
        )
        context['dosen_list'] = User.objects.filter(
            role='dosen', kode_fakultas=user.kode_fakultas, status_akun='aktif'
        ).order_by('kode_prodi', 'first_name')

    elif user.role in ['kaprodi', 'sekprodi', 'operator']:
        context['dosen_list'] = User.objects.filter(
            role='dosen', kode_prodi=user.kode_prodi, status_akun='aktif'
        ).order_by('first_name')

    return render(request, 'dashboard/rekap.html', context)