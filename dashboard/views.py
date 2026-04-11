from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from accounts.models import User
from master.models import Fakultas, Prodi, TahunAkademik, Pengaturan
from profil.models import ProfilDosen
from kinerja.models import Penelitian, Publikasi, PKM, HKI, BKD, DokumenKinerja


def annotate_dokumen(qs, jenis):
    """Tambahkan dokumen_list ke setiap objek queryset"""
    result = list(qs)
    ids = [obj.id for obj in result]
    dokumen_qs = DokumenKinerja.objects.filter(
        jenis_kinerja=jenis, kinerja_id__in=ids
    ).order_by('jenis_dokumen')

    dok_map = {}
    for d in dokumen_qs:
        dok_map.setdefault(d.kinerja_id, []).append(d)

    for obj in result:
        obj.dokumen_list = dok_map.get(obj.id, [])
    return result


@login_required
def index(request):
    user = request.user
    context = {}
    
    if user.role in ['admin', 'rektorat', 'biro']:
        filter_tahun_awal = request.GET.get('tahun_awal', '')
        filter_tahun_akhir = request.GET.get('tahun_akhir', '')
        filter_semester_db = request.GET.get('filter_semester', '')

        tahun_list_all = TahunAkademik.objects.filter(status='aktif').order_by('urutan')

        if filter_tahun_awal and filter_tahun_akhir:
            tahun_range = list(TahunAkademik.objects.filter(
                tahun_akademik__gte=filter_tahun_awal,
                tahun_akademik__lte=filter_tahun_akhir,
                status='aktif'
            ).values_list('tahun_akademik', flat=True))
        elif filter_tahun_awal:
            tahun_range = [filter_tahun_awal]
        elif filter_tahun_akhir:
            tahun_range = [filter_tahun_akhir]
        else:
            tahun_range = []

        penelitian_qs = Penelitian.objects.all()
        publikasi_qs = Publikasi.objects.all()
        pkm_qs = PKM.objects.all()
        hki_qs = HKI.objects.all()
        bkd_qs = BKD.objects.all()

        if tahun_range:
            penelitian_qs = penelitian_qs.filter(tahun_akademik__in=tahun_range)
            publikasi_qs = publikasi_qs.filter(tahun_akademik__in=tahun_range)
            pkm_qs = pkm_qs.filter(tahun_akademik__in=tahun_range)
            hki_qs = hki_qs.filter(tahun_akademik__in=tahun_range)
            bkd_qs = bkd_qs.filter(tahun_akademik__in=tahun_range)

        if filter_semester_db:
            penelitian_qs = penelitian_qs.filter(semester=filter_semester_db)
            publikasi_qs = publikasi_qs.filter(semester=filter_semester_db)
            pkm_qs = pkm_qs.filter(semester=filter_semester_db)
            hki_qs = hki_qs.filter(semester=filter_semester_db)
            bkd_qs = bkd_qs.filter(semester=filter_semester_db)

        context['total_dosen'] = User.objects.filter(
            role='dosen', status_akun='aktif'
        ).count()
        context['total_fakultas'] = Fakultas.objects.filter(status='aktif').count()
        context['total_prodi'] = Prodi.objects.filter(status='aktif').count()
        context['total_penelitian'] = penelitian_qs.count()
        context['total_publikasi'] = publikasi_qs.count()
        context['total_pkm'] = pkm_qs.count()
        context['total_hki'] = hki_qs.count()
        context['dosen_list'] = User.objects.filter(
            role='dosen', status_akun='aktif'
        ).order_by('kode_fakultas', 'kode_prodi', 'first_name')[:10]

        context['filter_tahun_awal'] = filter_tahun_awal
        context['filter_tahun_akhir'] = filter_tahun_akhir
        context['filter_semester_db'] = filter_semester_db
        context['tahun_list_all'] = tahun_list_all

        # Grafik per fakultas
        fakultas_list = Fakultas.objects.filter(status='aktif').order_by('kode_fakultas')
        grafik_fakultas_labels = []
        grafik_fakultas_data = []
        for f in fakultas_list:
            count = User.objects.filter(
                role='dosen', kode_fakultas=f.kode_fakultas
            ).count()
            grafik_fakultas_labels.append(f.kode_fakultas)
            grafik_fakultas_data.append(count)
        context['grafik_fakultas_labels'] = grafik_fakultas_labels
        context['grafik_fakultas_data'] = grafik_fakultas_data

        # Grafik pendidikan
        pendidikan_choices = ['S1', 'S2', 'S3']
        grafik_pend_data = []
        for p in pendidikan_choices:
            count = ProfilDosen.objects.filter(pendidikan_terakhir=p).count()
            grafik_pend_data.append(count)
        context['grafik_pend_labels'] = pendidikan_choices
        context['grafik_pend_data'] = grafik_pend_data

        # Grafik jabfung
        jabfung_choices = [
            'Tenaga Pengajar', 'Asisten Ahli',
            'Lektor', 'Lektor Kepala', 'Guru Besar'
        ]
        grafik_jabfung_data = []
        for j in jabfung_choices:
            count = ProfilDosen.objects.filter(jabfung_aktif=j).count()
            grafik_jabfung_data.append(count)
        context['grafik_jabfung_labels'] = jabfung_choices
        context['grafik_jabfung_data'] = grafik_jabfung_data

        # Grafik status kepegawaian
        status_choices = [
            'Aktif', 'Tugas Belajar', 'Lanjut Studi', 'Keluar', 'Meninggal'
        ]
        grafik_status_data = []
        for s in status_choices:
            count = User.objects.filter(role='dosen', status_kepegawaian=s).count()
            grafik_status_data.append(count)
        context['grafik_status_labels'] = status_choices
        context['grafik_status_data'] = grafik_status_data

    elif user.role in ['dekan', 'wadek']:
        context['total_dosen'] = User.objects.filter(
            role='dosen', kode_fakultas=user.kode_fakultas,
            status_akun='aktif'
        ).count()
        context['total_prodi'] = Prodi.objects.filter(
            fakultas_kode_fakultas=user.kode_fakultas, status='aktif'
        ).count()
        context['total_penelitian'] = Penelitian.objects.filter(
            kode_fakultas=user.kode_fakultas
        ).count()
        context['total_publikasi'] = Publikasi.objects.filter(
            kode_fakultas=user.kode_fakultas
        ).count()
        context['total_pkm'] = PKM.objects.filter(
            kode_fakultas=user.kode_fakultas
        ).count()
        context['total_hki'] = HKI.objects.filter(
            kode_fakultas=user.kode_fakultas
        ).count()

    elif user.role in ['kaprodi', 'sekprodi', 'operator']:
        context['total_dosen'] = User.objects.filter(
            role='dosen', kode_prodi=user.kode_prodi,
            status_akun='aktif'
        ).count()
        context['total_penelitian'] = Penelitian.objects.filter(
            kode_prodi=user.kode_prodi
        ).count()
        context['total_publikasi'] = Publikasi.objects.filter(
            kode_prodi=user.kode_prodi
        ).count()
        context['total_pkm'] = PKM.objects.filter(
            kode_prodi=user.kode_prodi
        ).count()
        context['total_hki'] = HKI.objects.filter(
            kode_prodi=user.kode_prodi
        ).count()
        context['dosen_list'] = User.objects.filter(
            role='dosen', kode_prodi=user.kode_prodi,
            status_akun='aktif'
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
        context['bkd_list'] = user.bkd_set.all().order_by(
            '-tahun_akademik', 'semester'
        )[:6]

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
    filter_tahun_awal = request.GET.get('tahun_awal', '')
    filter_tahun_akhir = request.GET.get('tahun_akhir', '')
    filter_semester = request.GET.get('semester', '') or request.GET.get('semester_rentang', '')
    filter_prodi = request.GET.get('prodi', '')
    filter_fakultas = request.GET.get('fakultas', '')
    filter_status = request.GET.get('status_kepegawaian', '')
    active_tab = request.GET.get('tab', 'dosen')
    mode_filter = request.GET.get('mode_filter', 'tunggal')

    # Hitung tahun range
    if filter_tahun:
        tahun_range = [filter_tahun]
    elif filter_tahun_awal and filter_tahun_akhir:
        tahun_range = list(TahunAkademik.objects.filter(
            tahun_akademik__gte=filter_tahun_awal,
            tahun_akademik__lte=filter_tahun_akhir,
            status='aktif'
        ).values_list('tahun_akademik', flat=True))
    else:
        tahun_range = []

    tahun_list = TahunAkademik.objects.filter(status='aktif').order_by('-urutan')
    fakultas_list = Fakultas.objects.filter(status='aktif').order_by('kode_fakultas')
    prodi_list = Prodi.objects.filter(status='aktif').order_by('kode_prodi')

    # Queryset sesuai role
    if user.role in ['admin', 'rektorat', 'biro']:
        dosen_qs = User.objects.filter(role='dosen')
        penelitian_qs = Penelitian.objects.all()
        publikasi_qs = Publikasi.objects.all()
        pkm_qs = PKM.objects.all()
        hki_qs = HKI.objects.all()
        bkd_qs = BKD.objects.all()
    elif user.role in ['dekan', 'wadek']:
        dosen_qs = User.objects.filter(
            role='dosen', kode_fakultas=user.kode_fakultas
        )
        prodi_list = prodi_list.filter(
            fakultas__kode_fakultas=user.kode_fakultas
        )
        penelitian_qs = Penelitian.objects.filter(
            kode_fakultas=user.kode_fakultas
        )
        publikasi_qs = Publikasi.objects.filter(
            kode_fakultas=user.kode_fakultas
        )
        pkm_qs = PKM.objects.filter(kode_fakultas=user.kode_fakultas)
        hki_qs = HKI.objects.filter(kode_fakultas=user.kode_fakultas)
        bkd_qs = BKD.objects.filter(
            user__kode_fakultas=user.kode_fakultas
        )
    elif user.role in ['kaprodi', 'sekprodi', 'operator']:
        dosen_qs = User.objects.filter(
            role='dosen', kode_prodi=user.kode_prodi
        )
        prodi_list = prodi_list.filter(kode_prodi=user.kode_prodi)
        penelitian_qs = Penelitian.objects.filter(kode_prodi=user.kode_prodi)
        publikasi_qs = Publikasi.objects.filter(kode_prodi=user.kode_prodi)
        pkm_qs = PKM.objects.filter(kode_prodi=user.kode_prodi)
        hki_qs = HKI.objects.filter(kode_prodi=user.kode_prodi)
        bkd_qs = BKD.objects.filter(user__kode_prodi=user.kode_prodi)
    else:
        dosen_qs = User.objects.none()
        penelitian_qs = Penelitian.objects.none()
        publikasi_qs = Publikasi.objects.none()
        pkm_qs = PKM.objects.none()
        hki_qs = HKI.objects.none()
        bkd_qs = BKD.objects.none()

    # Terapkan filter
    if filter_prodi:
        dosen_qs = dosen_qs.filter(kode_prodi=filter_prodi)
        penelitian_qs = penelitian_qs.filter(kode_prodi=filter_prodi)
        publikasi_qs = publikasi_qs.filter(kode_prodi=filter_prodi)
        pkm_qs = pkm_qs.filter(kode_prodi=filter_prodi)
        hki_qs = hki_qs.filter(kode_prodi=filter_prodi)
        bkd_qs = bkd_qs.filter(user__kode_prodi=filter_prodi)

    if filter_fakultas:
        dosen_qs = dosen_qs.filter(kode_fakultas=filter_fakultas)
        penelitian_qs = penelitian_qs.filter(kode_fakultas=filter_fakultas)
        publikasi_qs = publikasi_qs.filter(kode_fakultas=filter_fakultas)
        pkm_qs = pkm_qs.filter(kode_fakultas=filter_fakultas)
        hki_qs = hki_qs.filter(kode_fakultas=filter_fakultas)
        bkd_qs = bkd_qs.filter(user__kode_fakultas=filter_fakultas)

    if filter_status:
        dosen_qs = dosen_qs.filter(status_kepegawaian=filter_status)

    if tahun_range:
        penelitian_qs = penelitian_qs.filter(tahun_akademik__in=tahun_range)
        publikasi_qs = publikasi_qs.filter(tahun_akademik__in=tahun_range)
        pkm_qs = pkm_qs.filter(tahun_akademik__in=tahun_range)
        hki_qs = hki_qs.filter(tahun_akademik__in=tahun_range)
        bkd_qs = bkd_qs.filter(tahun_akademik__in=tahun_range)

    if filter_semester:
        penelitian_qs = penelitian_qs.filter(semester=filter_semester)
        publikasi_qs = publikasi_qs.filter(semester=filter_semester)
        pkm_qs = pkm_qs.filter(semester=filter_semester)
        hki_qs = hki_qs.filter(semester=filter_semester)
        bkd_qs = bkd_qs.filter(semester=filter_semester)

    # Order
    dosen_qs = dosen_qs.order_by('kode_fakultas', 'kode_prodi', 'first_name')
    penelitian_qs = penelitian_qs.select_related('user').order_by(
        '-tahun_akademik', 'user__first_name'
    )
    publikasi_qs = publikasi_qs.select_related('user').order_by(
        '-tahun_akademik', 'user__first_name'
    )
    pkm_qs = pkm_qs.select_related('user').order_by(
        '-tahun_akademik', 'user__first_name'
    )
    hki_qs = hki_qs.select_related('user').order_by(
        '-tahun_akademik', 'user__first_name'
    )
    bkd_qs = bkd_qs.select_related('user').order_by(
        '-tahun_akademik', 'user__first_name'
    )

    # Rekap per dosen
    rekap_data = []
    for dosen in dosen_qs:
        try:
            profil = dosen.profil
            kelengkapan = profil.persentase_kelengkapan
            jabfung = profil.jabfung_aktif or '-'
            pendidikan = profil.pendidikan_terakhir or '-'
        except Exception:
            kelengkapan = 0
            jabfung = '-'
            pendidikan = '-'

        d_penelitian = penelitian_qs.filter(user=dosen)
        d_publikasi = publikasi_qs.filter(user=dosen)
        d_pkm = pkm_qs.filter(user=dosen)
        d_hki = hki_qs.filter(user=dosen)
        d_bkd = bkd_qs.filter(user=dosen)

        rekap_data.append({
            'dosen': dosen,
            'jabfung': jabfung,
            'pendidikan': pendidikan,
            'kelengkapan': kelengkapan,
            'total_penelitian': d_penelitian.count(),
            'total_publikasi': d_publikasi.count(),
            'total_pkm': d_pkm.count(),
            'total_hki': d_hki.count(),
            'total_bkd': d_bkd.count(),
        })

    # Annotate dokumen ke setiap objek kinerja
    penelitian_annotated = annotate_dokumen(penelitian_qs, 'penelitian')
    publikasi_annotated = annotate_dokumen(publikasi_qs, 'publikasi')
    pkm_annotated = annotate_dokumen(pkm_qs, 'pkm')
    hki_annotated = annotate_dokumen(hki_qs, 'hki')
    bkd_annotated = annotate_dokumen(bkd_qs, 'bkd')

    # Pagination per tab
    from django.core.paginator import Paginator
    per_halaman = int(request.GET.get('per_halaman', 15))

    if active_tab == 'penelitian':
        paginator = Paginator(penelitian_annotated, per_halaman)
    elif active_tab == 'publikasi':
        paginator = Paginator(publikasi_annotated, per_halaman)
    elif active_tab == 'pkm':
        paginator = Paginator(pkm_annotated, per_halaman)
    elif active_tab == 'hki':
        paginator = Paginator(hki_annotated, per_halaman)
    elif active_tab == 'bkd':
        paginator = Paginator(bkd_annotated, per_halaman)
    else:
        paginator = Paginator(rekap_data, per_halaman)

    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'rekap_data': page_obj if active_tab == 'dosen' else rekap_data,
        'penelitian_list': page_obj if active_tab == 'penelitian' else penelitian_annotated[:5],
        'publikasi_list': page_obj if active_tab == 'publikasi' else publikasi_annotated[:5],
        'pkm_list': page_obj if active_tab == 'pkm' else pkm_annotated[:5],
        'hki_list': page_obj if active_tab == 'hki' else hki_annotated[:5],
        'bkd_list': page_obj if active_tab == 'bkd' else bkd_annotated[:5],
        'page_obj': page_obj,
        'active_tab': active_tab,
        'mode_filter': mode_filter,
        'tahun_list': tahun_list,
        'fakultas_list': fakultas_list,
        'prodi_list': prodi_list,
        'filter_tahun': filter_tahun,
        'filter_tahun_awal': filter_tahun_awal,
        'filter_tahun_akhir': filter_tahun_akhir,
        'filter_semester': filter_semester,
        'filter_prodi': filter_prodi,
        'filter_fakultas': filter_fakultas,
        'filter_status': filter_status,
        'total_dosen': len(rekap_data),
        'total_penelitian': penelitian_qs.count(),
        'total_publikasi': publikasi_qs.count(),
        'total_pkm': pkm_qs.count(),
        'total_hki': hki_qs.count(),
        'total_bkd': bkd_qs.count(),
        'per_halaman': str(per_halaman),
    }
    return render(request, 'dashboard/rekap.html', context)