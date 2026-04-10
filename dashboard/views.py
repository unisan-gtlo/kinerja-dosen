from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from accounts.models import User
from master.models import Fakultas, Prodi, TahunAkademik, Pengaturan
from profil.models import ProfilDosen
from kinerja.models import Penelitian, Publikasi, PKM, HKI, BKD


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

        # Data grafik per fakultas
        fakultas_list = Fakultas.objects.filter(status='aktif').order_by('kode_fakultas')
        grafik_fakultas_labels = []
        grafik_fakultas_data = []
        for f in fakultas_list:
            count = User.objects.filter(role='dosen', kode_fakultas=f.kode_fakultas).count()
            grafik_fakultas_labels.append(f.kode_fakultas)
            grafik_fakultas_data.append(count)
        context['grafik_fakultas_labels'] = grafik_fakultas_labels
        context['grafik_fakultas_data'] = grafik_fakultas_data

        # Data grafik pendidikan
        pendidikan_choices = ['S1', 'S2', 'S3']
        grafik_pend_data = []
        for p in pendidikan_choices:
            from django.db.models import Count
            count = ProfilDosen.objects.filter(pendidikan_terakhir=p).count()
            grafik_pend_data.append(count)
        context['grafik_pend_labels'] = pendidikan_choices
        context['grafik_pend_data'] = grafik_pend_data

        # Data grafik jabfung
        jabfung_choices = ['Tenaga Pengajar', 'Asisten Ahli', 'Lektor', 'Lektor Kepala', 'Guru Besar']
        grafik_jabfung_data = []
        for j in jabfung_choices:
            count = ProfilDosen.objects.filter(jabfung_aktif=j).count()
            grafik_jabfung_data.append(count)
        context['grafik_jabfung_labels'] = jabfung_choices
        context['grafik_jabfung_data'] = grafik_jabfung_data

        # Data grafik status kepegawaian
        status_choices = ['Aktif', 'Tugas Belajar', 'Lanjut Studi', 'Keluar', 'Meninggal']
        grafik_status_data = []
        for s in status_choices:
            count = User.objects.filter(role='dosen', status_kepegawaian=s).count()
            grafik_status_data.append(count)
        context['grafik_status_labels'] = status_choices
        context['grafik_status_data'] = grafik_status_data
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
            context['profil'] = profil
        except Exception:
            context['kelengkapan'] = 0
            context['profil'] = None

        context['total_penelitian'] = user.penelitian_set.count()
        context['total_publikasi'] = user.publikasi_set.count()
        context['total_pkm'] = user.pkm_set.count()
        context['total_hki'] = user.hki_set.count()
        context['total_bkd'] = user.bkd_set.count()
        context['bkd_list'] = user.bkd_set.all().order_by('-tahun_akademik', 'semester')[:6]

        try:
            prodi_obj = Prodi.objects.get(kode_prodi=user.kode_prodi)
            context['nama_prodi'] = prodi_obj.nama_prodi
        except Exception:
            context['nama_prodi'] = user.kode_prodi or '-'

    return render(request, 'dashboard/index.html', context)


@login_required
def rekap(request):
    user = request.user

    filter_tahun = request.GET.get('tahun', '')
    filter_semester = request.GET.get('semester', '')
    filter_prodi = request.GET.get('prodi', '')
    filter_fakultas = request.GET.get('fakultas', '')
    filter_status = request.GET.get('status_kepegawaian', '')

    tahun_list = TahunAkademik.objects.filter(status='aktif').order_by('-urutan')
    fakultas_list = Fakultas.objects.filter(status='aktif').order_by('kode_fakultas')
    prodi_list = Prodi.objects.filter(status='aktif').order_by('kode_prodi')

    if user.role in ['admin', 'rektorat', 'biro']:
        dosen_qs = User.objects.filter(role='dosen')
    elif user.role in ['dekan', 'wadek']:
        dosen_qs = User.objects.filter(role='dosen', kode_fakultas=user.kode_fakultas)
        prodi_list = prodi_list.filter(fakultas__kode_fakultas=user.kode_fakultas)
    elif user.role in ['kaprodi', 'sekprodi', 'operator']:
        dosen_qs = User.objects.filter(role='dosen', kode_prodi=user.kode_prodi)
        prodi_list = prodi_list.filter(kode_prodi=user.kode_prodi)
    else:
        dosen_qs = User.objects.none()

    if filter_prodi:
        dosen_qs = dosen_qs.filter(kode_prodi=filter_prodi)
    if filter_fakultas:
        dosen_qs = dosen_qs.filter(kode_fakultas=filter_fakultas)
    if filter_status:
        dosen_qs = dosen_qs.filter(status_kepegawaian=filter_status)

    dosen_qs = dosen_qs.order_by('kode_fakultas', 'kode_prodi', 'first_name')

    rekap_data = []
    for dosen in dosen_qs:
        penelitian_qs = dosen.penelitian_set.all()
        publikasi_qs = dosen.publikasi_set.all()
        pkm_qs = dosen.pkm_set.all()
        hki_qs = dosen.hki_set.all()
        bkd_qs = dosen.bkd_set.all()

        if filter_tahun:
            penelitian_qs = penelitian_qs.filter(tahun_akademik=filter_tahun)
            publikasi_qs = publikasi_qs.filter(tahun_akademik=filter_tahun)
            pkm_qs = pkm_qs.filter(tahun_akademik=filter_tahun)
            hki_qs = hki_qs.filter(tahun_akademik=filter_tahun)
            bkd_qs = bkd_qs.filter(tahun_akademik=filter_tahun)

        if filter_semester:
            penelitian_qs = penelitian_qs.filter(semester=filter_semester)
            publikasi_qs = publikasi_qs.filter(semester=filter_semester)
            pkm_qs = pkm_qs.filter(semester=filter_semester)
            hki_qs = hki_qs.filter(semester=filter_semester)
            bkd_qs = bkd_qs.filter(semester=filter_semester)

        try:
            profil = dosen.profil
            kelengkapan = profil.persentase_kelengkapan
            jabfung = profil.jabfung_aktif or '-'
            pendidikan = profil.pendidikan_terakhir or '-'
        except Exception:
            kelengkapan = 0
            jabfung = '-'
            pendidikan = '-'

        rekap_data.append({
            'dosen': dosen,
            'jabfung': jabfung,
            'pendidikan': pendidikan,
            'kelengkapan': kelengkapan,
            'total_penelitian': penelitian_qs.count(),
            'total_publikasi': publikasi_qs.count(),
            'total_pkm': pkm_qs.count(),
            'total_hki': hki_qs.count(),
            'total_bkd': bkd_qs.count(),
        })

    context = {
        'rekap_data': rekap_data,
        'tahun_list': tahun_list,
        'fakultas_list': fakultas_list,
        'prodi_list': prodi_list,
        'filter_tahun': filter_tahun,
        'filter_semester': filter_semester,
        'filter_prodi': filter_prodi,
        'filter_fakultas': filter_fakultas,
        'filter_status': filter_status,
        'total_dosen': len(rekap_data),
    }
    return render(request, 'dashboard/rekap.html', context)