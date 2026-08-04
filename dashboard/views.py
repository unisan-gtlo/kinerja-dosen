from django.db.models import Q
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from accounts.models import User
from master.models import Fakultas, Prodi, TahunAkademik, Pengaturan
from simda_dosen.models import (
    DataDosen, RiwayatBKD, RiwayatPangkatGolongan, JabatanFungsionalPublik,
    GolonganPublik, JenisKepegawaianPublik, StatusKepegawaianPublik,
)
from simda_dosen.utils import (
    get_simda_dosen_or_none, get_simda_tendik_or_none, filter_dosen_qs_by_kepegawaian, attach_kepegawaian_labels,
)
from presensi.models import IzinCuti, Presensi
from presensi.rekap import rekap_bulanan_user
from kinerja.models import DokumenKinerja
from penelitian.models import Penelitian, PublikasiKarya as Publikasi, PatenHki as HKI
from pengabdian.models import Pengabdian as PKM, Pembicara, PengelolaJurnal, JabatanStruktural
from pendidikan.models import (
    Pengajaran, BimbinganMahasiswa, PengujianMahasiswa, BahanAjar,
    PembinaanMahasiswa, OrasiIlmiah, TugasTambahan,
)
from penunjang.models import AnggotaProfesi, Penghargaan, PenunjangLain
from reward.models import Beasiswa, Kesejahteraan, Tunjangan
from profil.models import Sertifikasi


# Kategori "long-tail" untuk tab generik di Rekap admin -- Penelitian/
# Publikasi/PKM/HKI/BKD tetap pakai tab detail khusus (kode lama, field
# lengkap per kategori), sisanya pakai satu template generik supaya tidak
# perlu duplikasi ~20x pola tab yang sama. periode_mode menentukan cara
# filter tahun/semester: 'semester_tahun' pakai field semester+tahun_akademik
# (mayoritas kategori), 'tahun_mulai' pakai field tahun_mulai polos (Reward --
# tidak semester-bound sesuai form SISTER aslinya, jadi tidak difilter tahun/semester).
REKAP_CATEGORIES = [
    {'key': 'pengajaran', 'model': Pengajaran, 'label': 'Pengajaran', 'judul_field': 'nama_mk', 'periode_mode': 'semester_tahun', 'group': 'Pendidikan'},
    {'key': 'bimbingan_mahasiswa', 'model': BimbinganMahasiswa, 'label': 'Bimbingan Mahasiswa', 'judul_field': 'judul_bimbingan', 'periode_mode': 'semester_tahun', 'group': 'Pendidikan'},
    {'key': 'pengujian_mahasiswa', 'model': PengujianMahasiswa, 'label': 'Pengujian Mahasiswa', 'judul_field': 'judul_pengujian', 'periode_mode': 'semester_tahun', 'group': 'Pendidikan'},
    {'key': 'bahan_ajar', 'model': BahanAjar, 'label': 'Bahan Ajar', 'judul_field': 'judul', 'periode_mode': 'semester_tahun', 'group': 'Pendidikan'},
    {'key': 'pembinaan_mahasiswa', 'model': PembinaanMahasiswa, 'label': 'Pembinaan Mahasiswa', 'judul_field': 'nama_kegiatan', 'periode_mode': 'semester_tahun', 'group': 'Pendidikan'},
    {'key': 'orasi_ilmiah', 'model': OrasiIlmiah, 'label': 'Orasi Ilmiah', 'judul_field': 'judul_orasi', 'periode_mode': 'semester_tahun', 'group': 'Pendidikan'},
    {'key': 'tugas_tambahan', 'model': TugasTambahan, 'label': 'Tugas Tambahan', 'judul_field': 'jabatan_tambahan', 'periode_mode': 'semester_tahun', 'group': 'Pendidikan'},

    {'key': 'pembicara', 'model': Pembicara, 'label': 'Pembicara', 'judul_field': 'judul_makalah', 'periode_mode': 'semester_tahun', 'group': 'Pengabdian'},
    {'key': 'pengelola_jurnal', 'model': PengelolaJurnal, 'label': 'Pengelola Jurnal', 'judul_field': 'nama_jurnal', 'periode_mode': 'semester_tahun', 'group': 'Pengabdian'},
    {'key': 'jabatan_struktural', 'model': JabatanStruktural, 'label': 'Jabatan Struktural', 'judul_field': 'jabatan_tugas', 'periode_mode': 'semester_tahun', 'group': 'Pengabdian'},

    {'key': 'anggota_profesi', 'model': AnggotaProfesi, 'label': 'Anggota Profesi', 'judul_field': 'nama_organisasi', 'periode_mode': 'semester_tahun', 'group': 'Penunjang'},
    {'key': 'penghargaan', 'model': Penghargaan, 'label': 'Penghargaan', 'judul_field': 'nama_penghargaan', 'periode_mode': 'semester_tahun', 'group': 'Penunjang'},
    {'key': 'penunjang', 'model': PenunjangLain, 'label': 'Penunjang Lain', 'judul_field': 'nama_kegiatan', 'periode_mode': 'semester_tahun', 'group': 'Penunjang'},

    {'key': 'beasiswa', 'model': Beasiswa, 'label': 'Beasiswa', 'judul_field': 'nama_beasiswa', 'periode_mode': 'tahun_mulai', 'group': 'Reward'},
    {'key': 'kesejahteraan', 'model': Kesejahteraan, 'label': 'Kesejahteraan', 'judul_field': 'layanan_kesejahteraan', 'periode_mode': 'tahun_mulai', 'group': 'Reward'},
    {'key': 'tunjangan', 'model': Tunjangan, 'label': 'Tunjangan', 'judul_field': 'nama_tunjangan', 'periode_mode': 'tahun_mulai', 'group': 'Reward'},
]
REKAP_CATEGORIES_BY_KEY = {c['key']: c for c in REKAP_CATEGORIES}


def _generic_category_queryset(cat, user, filter_prodi, filter_fakultas, tahun_range, filter_semester):
    model = cat['model']
    if user.role in ['admin', 'rektorat', 'biro']:
        qs = model.objects.all()
    elif user.role in ['dekan', 'wadek', 'operator']:
        qs = model.objects.filter(kode_fakultas=user.kode_fakultas)
    elif user.role in ['kaprodi', 'sekprodi']:
        qs = model.objects.filter(kode_prodi=user.kode_prodi)
    else:
        qs = model.objects.none()

    if filter_prodi:
        qs = qs.filter(kode_prodi=filter_prodi)
    if filter_fakultas:
        qs = qs.filter(kode_fakultas=filter_fakultas)

    if cat['periode_mode'] == 'semester_tahun':
        if tahun_range:
            qs = qs.filter(tahun_akademik__in=tahun_range)
        if filter_semester:
            qs = qs.filter(semester=filter_semester)

    return qs.select_related('user').order_by('-id')


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
        bkd_qs = RiwayatBKD.objects.using('simda').all()

        if tahun_range:
            penelitian_qs = penelitian_qs.filter(tahun_akademik__in=tahun_range)
            publikasi_qs = publikasi_qs.filter(tahun_akademik__in=tahun_range)
            pkm_qs = pkm_qs.filter(tahun_akademik__in=tahun_range)
            hki_qs = hki_qs.filter(tahun_akademik__in=tahun_range)
            bkd_qs = bkd_qs.filter(periode__tahun_akademik__in=tahun_range)

        if filter_semester_db:
            penelitian_qs = penelitian_qs.filter(semester=filter_semester_db)
            publikasi_qs = publikasi_qs.filter(semester=filter_semester_db)
            pkm_qs = pkm_qs.filter(semester=filter_semester_db)
            hki_qs = hki_qs.filter(semester=filter_semester_db)
            bkd_qs = bkd_qs.filter(periode__semester_aktif=filter_semester_db)

        context['total_dosen'] = User.objects.filter(
            role='dosen', status_akun='aktif'
        ).count()
        context['total_fakultas'] = Fakultas.objects.filter(status='aktif').count()
        context['total_prodi'] = Prodi.objects.filter(status='aktif').count()
        context['total_penelitian'] = penelitian_qs.count()
        context['total_publikasi'] = publikasi_qs.count()
        context['total_pkm'] = pkm_qs.count()
        context['total_hki'] = hki_qs.count()
        context['dosen_list'] = attach_kepegawaian_labels(User.objects.filter(
            role='dosen', status_akun='aktif'
        ).order_by('kode_fakultas', 'kode_prodi', 'first_name')[:10])

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
            count = DataDosen.objects.using('simda').filter(pendidikan_terakhir=p).count()
            grafik_pend_data.append(count)
        context['grafik_pend_labels'] = pendidikan_choices
        context['grafik_pend_data'] = grafik_pend_data

        # Grafik jabfung -- nama jabfung dicocokkan ke id via view referensi SIMDA
        jabfung_ref = {
            jf.nama: jf.id for jf in JabatanFungsionalPublik.objects.using('simda').all()
        }
        jabfung_choices = list(jabfung_ref.keys())
        grafik_jabfung_data = []
        for j in jabfung_choices:
            count = DataDosen.objects.using('simda').filter(jabatan_fungsional_id=jabfung_ref[j]).count()
            grafik_jabfung_data.append(count)
        context['grafik_jabfung_labels'] = jabfung_choices
        context['grafik_jabfung_data'] = grafik_jabfung_data

        # Grafik status keaktifan -- sumbernya DataDosen SIMDA (mengikuti
        # pola grafik jabfung/pendidikan di atas), bukan lagi User lokal.
        status_ref = list(StatusKepegawaianPublik.objects.using('simda').all())
        grafik_status_labels = [s.nama for s in status_ref]
        grafik_status_data = [
            DataDosen.objects.using('simda').filter(status_kepegawaian_id=s.id).count()
            for s in status_ref
        ]
        context['grafik_status_labels'] = grafik_status_labels
        context['grafik_status_data'] = grafik_status_data

    elif user.role in ['dekan', 'wadek', 'operator']:
        context['total_dosen'] = User.objects.filter(
            role='dosen', kode_fakultas=user.kode_fakultas,
            status_akun='aktif'
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
        context['total_pkm'] = PKM.objects.filter(
            kode_fakultas=user.kode_fakultas
        ).count()
        context['total_hki'] = HKI.objects.filter(
            kode_fakultas=user.kode_fakultas
        ).count()

    elif user.role in ['kaprodi', 'sekprodi']:
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
        context['dosen_list'] = attach_kepegawaian_labels(User.objects.filter(
            role='dosen', kode_prodi=user.kode_prodi,
            status_akun='aktif'
        ).order_by('first_name'))

    elif user.role == 'dosen':
        profil = get_simda_dosen_or_none(user)
        if profil:
            context['kelengkapan'] = profil.persentase_kelengkapan
            context['profil'] = profil
            context['total_bkd'] = profil.riwayat_bkd.count()
            context['bkd_list'] = profil.riwayat_bkd.all().order_by('-periode__urutan')[:6]
        else:
            context['kelengkapan'] = 0
            context['profil'] = None
            context['total_bkd'] = 0
            context['bkd_list'] = RiwayatBKD.objects.none()

        context['total_penelitian'] = user.penelitian_set.count()
        context['total_publikasi'] = user.publikasi_set.count()
        context['total_pkm'] = user.pkm_set.count()
        context['total_hki'] = user.hki_set.count()

        try:
            prodi_obj = Prodi.objects.get(kode_prodi=user.kode_prodi)
            context['nama_prodi'] = prodi_obj.nama_prodi
        except Exception:
            context['nama_prodi'] = user.kode_prodi or '-'

    elif user.role == 'tendik':
        # Tendik TIDAK punya data Tri Dharma (Penelitian/Pengabdian/dst) --
        # dashboard-nya sengaja beda total dari dosen maupun dashboard
        # oversight admin/dekan/dst (yang isinya rekap dosen lain, tidak
        # relevan buat tendik). Fokus ke ringkasan presensi diri sendiri,
        # reuse rekap_bulanan_user (presensi/rekap.py) -- tidak ada logika
        # baru untuk itu.
        hari_ini = timezone.localdate()
        context['tendik_profil'] = get_simda_tendik_or_none(user)
        context['rekap_bulan_ini'] = rekap_bulanan_user(user, hari_ini.month, hari_ini.year)
        context['presensi_hari_ini'] = Presensi.objects.filter(user=user, tanggal=hari_ini).first()
        context['izin_menunggu'] = IzinCuti.objects.filter(
            user=user, status=IzinCuti.StatusApproval.MENUNGGU,
        ).count()
        context['izin_terbaru'] = IzinCuti.objects.filter(user=user).order_by('-dibuat')[:5]

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
    filter_jenis_kepegawaian = request.GET.get('jenis_kepegawaian', '')
    filter_status_kepegawaian = request.GET.get('status_kepegawaian', '')
    filter_nama = request.GET.get('nama', '').strip()
    filter_pendidikan = request.GET.get('pendidikan', '')
    filter_golongan = request.GET.get('golongan', '')
    filter_jabfung = request.GET.get('jabfung', '')
    filter_sertifikasi = request.GET.get('sertifikasi', '')
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
        bkd_qs = RiwayatBKD.objects.using('simda').all()
    elif user.role in ['dekan', 'wadek', 'operator']:
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
        bkd_qs = RiwayatBKD.objects.using('simda').filter(
            dosen__kode_fakultas=user.kode_fakultas
        )
    elif user.role in ['kaprodi', 'sekprodi']:
        dosen_qs = User.objects.filter(
            role='dosen', kode_prodi=user.kode_prodi
        )
        prodi_list = prodi_list.filter(kode_prodi=user.kode_prodi)
        penelitian_qs = Penelitian.objects.filter(kode_prodi=user.kode_prodi)
        publikasi_qs = Publikasi.objects.filter(kode_prodi=user.kode_prodi)
        pkm_qs = PKM.objects.filter(kode_prodi=user.kode_prodi)
        hki_qs = HKI.objects.filter(kode_prodi=user.kode_prodi)
        bkd_qs = RiwayatBKD.objects.using('simda').filter(dosen__kode_prodi=user.kode_prodi)
    else:
        dosen_qs = User.objects.none()
        penelitian_qs = Penelitian.objects.none()
        publikasi_qs = Publikasi.objects.none()
        pkm_qs = PKM.objects.none()
        hki_qs = HKI.objects.none()
        bkd_qs = RiwayatBKD.objects.none()

    # Terapkan filter
    if filter_prodi:
        dosen_qs = dosen_qs.filter(kode_prodi=filter_prodi)
        penelitian_qs = penelitian_qs.filter(kode_prodi=filter_prodi)
        publikasi_qs = publikasi_qs.filter(kode_prodi=filter_prodi)
        pkm_qs = pkm_qs.filter(kode_prodi=filter_prodi)
        hki_qs = hki_qs.filter(kode_prodi=filter_prodi)
        bkd_qs = bkd_qs.filter(dosen__kode_prodi=filter_prodi)

    if filter_fakultas:
        dosen_qs = dosen_qs.filter(kode_fakultas=filter_fakultas)
        penelitian_qs = penelitian_qs.filter(kode_fakultas=filter_fakultas)
        publikasi_qs = publikasi_qs.filter(kode_fakultas=filter_fakultas)
        pkm_qs = pkm_qs.filter(kode_fakultas=filter_fakultas)
        hki_qs = hki_qs.filter(kode_fakultas=filter_fakultas)
        bkd_qs = bkd_qs.filter(dosen__kode_fakultas=filter_fakultas)

    if filter_jenis_kepegawaian or filter_status_kepegawaian:
        dosen_qs = filter_dosen_qs_by_kepegawaian(
            dosen_qs, filter_jenis_kepegawaian, filter_status_kepegawaian
        )

    if filter_nama:
        nidn_by_nama = list(DataDosen.objects.using('simda').filter(
            nama_lengkap__icontains=filter_nama
        ).values_list('nidn', flat=True))
        dosen_qs = dosen_qs.filter(
            Q(first_name__icontains=filter_nama) | Q(last_name__icontains=filter_nama) |
            Q(username__icontains=filter_nama) | Q(nidn__in=nidn_by_nama)
        )

    if filter_pendidikan:
        nidn_list = list(DataDosen.objects.using('simda').filter(
            pendidikan_terakhir=filter_pendidikan
        ).values_list('nidn', flat=True))
        dosen_qs = dosen_qs.filter(nidn__in=nidn_list)

    if filter_golongan:
        nidn_list = list(RiwayatPangkatGolongan.objects.using('simda').filter(
            golongan_id=filter_golongan
        ).values_list('dosen__nidn', flat=True))
        dosen_qs = dosen_qs.filter(nidn__in=nidn_list)

    if filter_jabfung:
        nidn_list = list(DataDosen.objects.using('simda').filter(
            jabatan_fungsional_id=filter_jabfung
        ).values_list('nidn', flat=True))
        dosen_qs = dosen_qs.filter(nidn__in=nidn_list)

    if filter_sertifikasi:
        user_ids = Sertifikasi.objects.filter(
            jenis_sertifikasi=filter_sertifikasi
        ).values_list('user_id', flat=True)
        dosen_qs = dosen_qs.filter(id__in=user_ids)

    if tahun_range:
        penelitian_qs = penelitian_qs.filter(tahun_akademik__in=tahun_range)
        publikasi_qs = publikasi_qs.filter(tahun_akademik__in=tahun_range)
        pkm_qs = pkm_qs.filter(tahun_akademik__in=tahun_range)
        hki_qs = hki_qs.filter(tahun_akademik__in=tahun_range)
        bkd_qs = bkd_qs.filter(periode__tahun_akademik__in=tahun_range)

    if filter_semester:
        penelitian_qs = penelitian_qs.filter(semester=filter_semester)
        publikasi_qs = publikasi_qs.filter(semester=filter_semester)
        pkm_qs = pkm_qs.filter(semester=filter_semester)
        hki_qs = hki_qs.filter(semester=filter_semester)
        bkd_qs = bkd_qs.filter(periode__semester_aktif=filter_semester)

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
    bkd_qs = bkd_qs.select_related('dosen').order_by(
        '-periode__tahun_akademik', 'dosen__nama_lengkap'
    )

    # Serdos -- diambil sekali di luar loop supaya tidak N+1 query per dosen.
    serdos_user_ids = set(Sertifikasi.objects.filter(
        user__in=dosen_qs, jenis_sertifikasi='serdos'
    ).values_list('user_id', flat=True))

    # Rekap per dosen
    rekap_data = []
    for dosen in dosen_qs:
        profil = get_simda_dosen_or_none(dosen)
        if profil:
            kelengkapan = profil.persentase_kelengkapan
            jabfung = profil.jabatan_fungsional_nama or '-'
            pendidikan = profil.pendidikan_terakhir or '-'
            # Nama lengkap + gelar dari SIMDA (master) -- bukan first_name/
            # last_name User SIKD yang sering belum diisi lengkap/tanpa gelar.
            nama_dosen = profil.nama_lengkap_gelar
            pangkat_terakhir = profil.riwayat_pangkat_golongan.first()
            golongan = pangkat_terakhir.golongan_display if pangkat_terakhir else '-'
            foto_url = profil.foto.url if profil.foto else ''
        else:
            kelengkapan = 0
            jabfung = '-'
            pendidikan = '-'
            nama_dosen = dosen.get_full_name() or dosen.username
            golongan = '-'
            foto_url = ''

        d_penelitian = penelitian_qs.filter(user=dosen)
        d_publikasi = publikasi_qs.filter(user=dosen)
        d_pkm = pkm_qs.filter(user=dosen)
        d_hki = hki_qs.filter(user=dosen)
        d_bkd = bkd_qs.filter(dosen__nidn=dosen.nidn) if dosen.nidn else bkd_qs.none()

        rekap_data.append({
            'dosen': dosen,
            'nama_dosen': nama_dosen,
            'foto_url': foto_url,
            'jabfung': jabfung,
            'pendidikan': pendidikan,
            'golongan': golongan,
            'has_serdos': dosen.id in serdos_user_ids,
            'kelengkapan': kelengkapan,
            'jenis_kepegawaian': profil.jenis_kepegawaian_nama if profil else '',
            'status_kepegawaian': profil.status_kepegawaian_nama if profil else '',
            'id_sinta': profil.id_sinta if profil else '',
            'id_scopus': profil.id_scopus if profil else '',
            'id_google_scholar': profil.id_google_scholar if profil else '',
            'orcid': profil.orcid if profil else '',
            'id_garuda': profil.id_garuda if profil else '',
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

    # Kategori generik (long-tail) -- dipakai kalau active_tab cocok salah
    # satu key di REKAP_CATEGORIES (lihat definisi di atas file ini).
    current_generic = None
    generic_cat = REKAP_CATEGORIES_BY_KEY.get(active_tab)
    if generic_cat:
        generic_qs = _generic_category_queryset(
            generic_cat, user, filter_prodi, filter_fakultas, tahun_range, filter_semester
        )
        generic_annotated = annotate_dokumen(generic_qs, generic_cat['key'])
        for obj in generic_annotated:
            obj.judul_tampil = getattr(obj, generic_cat['judul_field'], '') or '-'
        current_generic = {
            'key': generic_cat['key'],
            'label': generic_cat['label'],
            'group': generic_cat['group'],
            'list': generic_annotated,
            'total': len(generic_annotated),
        }

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
    elif current_generic:
        paginator = Paginator(current_generic['list'], per_halaman)
    else:
        paginator = Paginator(rekap_data, per_halaman)

    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    if current_generic:
        current_generic['list'] = page_obj

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
        'filter_jenis_kepegawaian': filter_jenis_kepegawaian,
        'filter_status_kepegawaian': filter_status_kepegawaian,
        'filter_nama': filter_nama,
        'filter_pendidikan': filter_pendidikan,
        'filter_golongan': filter_golongan,
        'filter_jabfung': filter_jabfung,
        'filter_sertifikasi': filter_sertifikasi,
        'jenis_kepegawaian_ref_list': JenisKepegawaianPublik.objects.using('simda').all(),
        'status_kepegawaian_ref_list': StatusKepegawaianPublik.objects.using('simda').all(),
        'golongan_ref_list': GolonganPublik.objects.using('simda').all(),
        'jabfung_ref_list': JabatanFungsionalPublik.objects.using('simda').all(),
        'sertifikasi_jenis_choices': Sertifikasi.JENIS_SERTIFIKASI,
        'total_dosen': len(rekap_data),
        'total_penelitian': penelitian_qs.count(),
        'total_publikasi': publikasi_qs.count(),
        'total_pkm': pkm_qs.count(),
        'total_hki': hki_qs.count(),
        'total_bkd': bkd_qs.count(),
        'per_halaman': str(per_halaman),
        'rekap_categories': REKAP_CATEGORIES,
        'current_generic': current_generic,
        'pengaturan': Pengaturan.objects.first(),
    }
    return render(request, 'dashboard/rekap.html', context)