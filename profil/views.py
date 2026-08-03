from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from master.models import TahunAkademik, Pengaturan
from accounts.models import User
from simda_dosen.models import (
    DataDosen, RiwayatJabatanFungsional, RiwayatPendidikanDosen,
    RiwayatPangkatGolongan, AgamaPublik, JabatanFungsionalPublik, GolonganPublik,
    BidangKeahlianPublik, JenisKepegawaianPublik, StatusKepegawaianPublik,
)
from simda_dosen.utils import (
    get_simda_dosen_or_none, dapat_kelola_nidn, get_or_create_bidang_keahlian,
    sync_jabfung_aktif, sync_pendidikan_terakhir, sync_golongan_terakhir,
    get_golongan_ref_list_dosen,
    resolve_target_user as resolve_target_user_util,
)
from simda_dosen.file_compress import compress_uploaded_file
from kinerja.utils import attach_dokumen_count
from .models import DokumenLain, Diklat, Sertifikasi, TesKompetensi

def cek_status_input():
    try:
        p = Pengaturan.objects.first()
        return p.status_input == 'buka' if p else True
    except:
        return True


def resolve_target_user(request, dosen_id):
    return resolve_target_user_util(request, dosen_id, 'profil:index')

@login_required
def index(request):
    user = request.user
    target_user = user

    dosen_id = request.GET.get('dosen_id')
    if dosen_id and user.role in ['admin', 'kaprodi', 'sekprodi', 'operator', 'dekan', 'wadek', 'rektorat', 'biro']:
        target_user = get_object_or_404(User, id=dosen_id)

    profil = get_simda_dosen_or_none(target_user)

    if profil:
        jabfung_list = profil.riwayat_jabfung.all().order_by('-tmt')
        pangkat_list = profil.riwayat_pangkat_golongan.all().order_by('-tmt')
        pendidikan_list = profil.riwayat_pendidikan.all().order_by('-tahun_lulus')
    else:
        jabfung_list = RiwayatJabatanFungsional.objects.none()
        pangkat_list = RiwayatPangkatGolongan.objects.none()
        pendidikan_list = RiwayatPendidikanDosen.objects.none()

    dokumen_list = target_user.dokumen_set.all().order_by('-tgl_input')
    tahun_list = TahunAkademik.objects.filter(status='aktif').order_by('-urutan')
    input_terbuka = cek_status_input()
    bisa_edit = user.dapat_kelola(target_user) and input_terbuka
    bisa_edit_kepegawaian = user.dapat_kelola(target_user) and input_terbuka
    has_serdos = Sertifikasi.objects.filter(
        user=target_user, jenis_sertifikasi='serdos'
    ).exists()

    context = {
        'target_user': target_user,
        'profil': profil,
        'jabfung_list': jabfung_list,
        'pangkat_list': pangkat_list,
        'pendidikan_list': pendidikan_list,
        'dokumen_list': dokumen_list,
        'tahun_list': tahun_list,
        'bisa_edit': bisa_edit,
        'bisa_edit_kepegawaian': bisa_edit_kepegawaian,
        'input_terbuka': input_terbuka,
        'has_serdos': has_serdos,
        'agama_list': AgamaPublik.objects.using('simda').all(),
        'jabfung_ref_list': JabatanFungsionalPublik.objects.using('simda').all(),
        'golongan_ref_list': get_golongan_ref_list_dosen(),
        'bidang_keahlian_ref_list': BidangKeahlianPublik.objects.using('simda').all(),
        'jenis_kepegawaian_ref_list': JenisKepegawaianPublik.objects.using('simda').all(),
        'status_kepegawaian_ref_list': StatusKepegawaianPublik.objects.using('simda').all(),
    }
    return render(request, 'profil/index.html', context)

@login_required
def simpan_profil(request):
    if request.method != 'POST':
        return redirect('profil:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci oleh admin.')
        return redirect('profil:index')

    user = request.user
    dosen_id = request.POST.get('dosen_id')
    target_user, err = resolve_target_user(request, dosen_id)
    if err:
        return err

    profil = get_simda_dosen_or_none(target_user)
    if not profil:
        messages.error(request, 'NIDN Anda belum cocok dengan data di SIMDA. Hubungi admin untuk membetulkan NIDN.')
        return redirect('profil:index')

    profil.nuptk = request.POST.get('nuptk', '').strip()
    profil.nama_lengkap = request.POST.get('nama_lengkap', '').strip() or profil.nama_lengkap
    profil.gelar_depan = request.POST.get('gelar_depan', '').strip()
    profil.gelar_belakang = request.POST.get('gelar_belakang', '').strip()
    profil.nik = request.POST.get('nik', '').strip()
    profil.tempat_lahir = request.POST.get('tempat_lahir', '').strip()
    profil.tgl_lahir = request.POST.get('tgl_lahir') or None
    profil.jenis_kelamin = request.POST.get('jenis_kelamin', '')
    profil.agama_id = request.POST.get('agama_id') or None
    profil.status_pernikahan = request.POST.get('status_pernikahan', '')
    profil.alamat_domisili = request.POST.get('alamat_domisili', '').strip()
    profil.kode_pos = request.POST.get('kode_pos', '').strip()
    profil.no_hp = request.POST.get('no_hp', '').strip()
    profil.email_pribadi = request.POST.get('email_pribadi', '').strip()
    profil.id_sinta = request.POST.get('id_sinta', '').strip()
    profil.id_scopus = request.POST.get('id_scopus', '').strip()
    profil.id_google_scholar = request.POST.get('id_google_scholar', '').strip()
    profil.orcid = request.POST.get('orcid', '').strip()
    profil.id_garuda = request.POST.get('id_garuda', '').strip()
    profil.h_index_sinta = request.POST.get('h_index_sinta') or None
    profil.h_index_scopus = request.POST.get('h_index_scopus') or None
    profil.nira = request.POST.get('nira', '').strip()
    profil.minat_penelitian = request.POST.get('minat_penelitian', '').strip()
    profil.npwp = request.POST.get('npwp', '').strip()
    profil.nama_bank = request.POST.get('nama_bank', '').strip()
    profil.no_rekening = request.POST.get('no_rekening', '').strip()
    profil.atas_nama_rekening = request.POST.get('atas_nama_rekening', '').strip()
    profil.bidang_keahlian_id = get_or_create_bidang_keahlian(
        request.POST.get('bidang_keahlian_nama', '')
    )
    profil.no_sk_pengangkatan = request.POST.get('no_sk_pengangkatan', '').strip()
    profil.tgl_sk_pengangkatan = request.POST.get('tgl_sk_pengangkatan') or None

    # Status Kepegawaian & Status Keaktifan -- ADMIN/HR, dosen tidak boleh
    # ubah status kepegawaiannya sendiri lewat form self-service ini.
    if user.dapat_kelola(target_user) and user != target_user:
        profil.jenis_kepegawaian_id = request.POST.get('jenis_kepegawaian_id') or None
        profil.status_kepegawaian_id = request.POST.get('status_kepegawaian_id') or None

    if 'foto' in request.FILES:
        profil.foto = compress_uploaded_file(request.FILES['foto'])
    if 'file_ktp' in request.FILES:
        profil.file_ktp = compress_uploaded_file(request.FILES['file_ktp'])
    if 'file_npwp' in request.FILES:
        profil.file_npwp = compress_uploaded_file(request.FILES['file_npwp'])
    if 'file_sk_pengangkatan' in request.FILES:
        profil.file_sk_pengangkatan = compress_uploaded_file(request.FILES['file_sk_pengangkatan'])

    profil.save()
    messages.success(request, 'Profil berhasil disimpan ke SIMDA.')
    return redirect('profil:index')

@login_required
def tambah_jabfung(request):
    if request.method != 'POST':
        return redirect('profil:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('profil:index')

    user = request.user
    dosen_id = request.POST.get('dosen_id')
    target_user, err = resolve_target_user(request, dosen_id)
    if err:
        return err
    dosen = get_simda_dosen_or_none(target_user)
    if not dosen:
        messages.error(request, 'NIDN Anda belum cocok dengan data di SIMDA. Hubungi admin.')
        return redirect('profil:index')

    jabfung = RiwayatJabatanFungsional(
        dosen=dosen,
        jabatan_fungsional_id=request.POST.get('jabatan_fungsional_id') or None,
        no_sk=request.POST.get('no_sk', '').strip(),
        tgl_sk=request.POST.get('tgl_sk') or None,
        tmt=request.POST.get('tmt') or None,
        url_sk=request.POST.get('url_sk', '').strip(),
        keterangan=request.POST.get('keterangan', '').strip(),
    )
    if 'file_sk' in request.FILES:
        jabfung.file_sk = compress_uploaded_file(request.FILES['file_sk'])
    jabfung.save()
    sync_jabfung_aktif(dosen)

    messages.success(request, 'Riwayat jabatan fungsional berhasil ditambahkan ke SIMDA.')
    return redirect('profil:index')

@login_required
def hapus_jabfung(request, jabfung_id):
    jabfung = get_object_or_404(RiwayatJabatanFungsional, id=jabfung_id)
    if not dapat_kelola_nidn(request.user, jabfung.dosen.nidn):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('profil:index')
    dosen = jabfung.dosen
    jabfung.delete()
    sync_jabfung_aktif(dosen)
    messages.success(request, 'Data jabatan berhasil dihapus.')
    return redirect('profil:index')

@login_required
def tambah_pangkat(request):
    if request.method != 'POST':
        return redirect('profil:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('profil:index')

    user = request.user
    dosen_id = request.POST.get('dosen_id')
    target_user, err = resolve_target_user(request, dosen_id)
    if err:
        return err
    dosen = get_simda_dosen_or_none(target_user)
    if not dosen:
        messages.error(request, 'NIDN Anda belum cocok dengan data di SIMDA. Hubungi admin.')
        return redirect('profil:index')

    pangkat = RiwayatPangkatGolongan(
        dosen=dosen,
        golongan_id=request.POST.get('golongan_id') or None,
        no_sk=request.POST.get('no_sk', '').strip(),
        tgl_sk=request.POST.get('tgl_sk') or None,
        tmt=request.POST.get('tmt') or None,
        angka_kredit=request.POST.get('angka_kredit') or 0,
        masa_kerja_tahun=request.POST.get('masa_kerja_tahun') or 0,
        masa_kerja_bulan=request.POST.get('masa_kerja_bulan') or 0,
        url_sk=request.POST.get('url_sk', '').strip(),
    )
    if 'file_sk' in request.FILES:
        pangkat.file_sk = compress_uploaded_file(request.FILES['file_sk'])
    pangkat.save()
    sync_golongan_terakhir(dosen)

    messages.success(request, 'Riwayat pangkat/golongan berhasil ditambahkan ke SIMDA.')
    return redirect('profil:index')

@login_required
def edit_pangkat(request, pangkat_id):
    pangkat = get_object_or_404(RiwayatPangkatGolongan, id=pangkat_id)
    if not dapat_kelola_nidn(request.user, pangkat.dosen.nidn):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('profil:index')
    if request.method == 'POST':
        pangkat.golongan_id = request.POST.get('golongan_id') or pangkat.golongan_id
        pangkat.no_sk = request.POST.get('no_sk', '').strip()
        pangkat.tgl_sk = request.POST.get('tgl_sk') or None
        pangkat.tmt = request.POST.get('tmt') or pangkat.tmt
        pangkat.angka_kredit = request.POST.get('angka_kredit') or pangkat.angka_kredit
        pangkat.masa_kerja_tahun = request.POST.get('masa_kerja_tahun') or 0
        pangkat.masa_kerja_bulan = request.POST.get('masa_kerja_bulan') or 0
        pangkat.url_sk = request.POST.get('url_sk', '').strip()
        if 'file_sk' in request.FILES:
            pangkat.file_sk = compress_uploaded_file(request.FILES['file_sk'])
        pangkat.save()
        sync_golongan_terakhir(pangkat.dosen)
        messages.success(request, 'Data pangkat/golongan berhasil diupdate.')
    return redirect('profil:index')

@login_required
def hapus_pangkat(request, pangkat_id):
    pangkat = get_object_or_404(RiwayatPangkatGolongan, id=pangkat_id)
    if not dapat_kelola_nidn(request.user, pangkat.dosen.nidn):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('profil:index')
    dosen = pangkat.dosen
    pangkat.delete()
    sync_golongan_terakhir(dosen)
    messages.success(request, 'Data pangkat/golongan berhasil dihapus.')
    return redirect('profil:index')

@login_required
def tambah_pendidikan(request):
    if request.method != 'POST':
        return redirect('profil:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('profil:index')

    user = request.user
    dosen_id = request.POST.get('dosen_id')
    target_user, err = resolve_target_user(request, dosen_id)
    if err:
        return err
    dosen = get_simda_dosen_or_none(target_user)
    if not dosen:
        messages.error(request, 'NIDN Anda belum cocok dengan data di SIMDA. Hubungi admin.')
        return redirect('profil:index')

    pend = RiwayatPendidikanDosen(
        dosen=dosen,
        jenjang=request.POST.get('jenjang', ''),
        institusi=request.POST.get('nama_pt', '').strip(),
        prodi_studi=request.POST.get('bidang_ilmu', '').strip(),
        tahun_masuk=request.POST.get('tahun_masuk') or None,
        tahun_lulus=request.POST.get('tahun_lulus') or None,
        no_ijazah=request.POST.get('no_ijazah', '').strip(),
        judul_thesis=request.POST.get('judul_thesis', '').strip(),
    )
    if 'file_ijazah' in request.FILES:
        pend.file_ijazah = compress_uploaded_file(request.FILES['file_ijazah'])
    if 'file_transkrip' in request.FILES:
        pend.file_transkrip = compress_uploaded_file(request.FILES['file_transkrip'])
    pend.save()
    sync_pendidikan_terakhir(dosen)
    messages.success(request, 'Data pendidikan berhasil ditambahkan ke SIMDA.')
    return redirect('profil:index')

@login_required
def hapus_pendidikan(request, pend_id):
    pend = get_object_or_404(RiwayatPendidikanDosen, id=pend_id)
    if not dapat_kelola_nidn(request.user, pend.dosen.nidn):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('profil:index')
    dosen = pend.dosen
    pend.delete()
    sync_pendidikan_terakhir(dosen)
    messages.success(request, 'Data pendidikan berhasil dihapus.')
    return redirect('profil:index')

@login_required
def edit_jabfung(request, jabfung_id):
    jabfung = get_object_or_404(RiwayatJabatanFungsional, id=jabfung_id)
    if not dapat_kelola_nidn(request.user, jabfung.dosen.nidn):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('profil:index')
    if request.method == 'POST':
        jabfung.jabatan_fungsional_id = request.POST.get('jabatan_fungsional_id') or jabfung.jabatan_fungsional_id
        jabfung.no_sk = request.POST.get('no_sk', '').strip()
        jabfung.tgl_sk = request.POST.get('tgl_sk') or None
        jabfung.tmt = request.POST.get('tmt') or None
        jabfung.url_sk = request.POST.get('url_sk', '').strip()
        jabfung.keterangan = request.POST.get('keterangan', '').strip()
        if 'file_sk' in request.FILES:
            jabfung.file_sk = compress_uploaded_file(request.FILES['file_sk'])
        jabfung.save()
        sync_jabfung_aktif(jabfung.dosen)
        messages.success(request, 'Data jabatan berhasil diupdate.')
    return redirect('profil:index')


@login_required
def edit_pendidikan(request, pend_id):
    pend = get_object_or_404(RiwayatPendidikanDosen, id=pend_id)
    if not dapat_kelola_nidn(request.user, pend.dosen.nidn):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('profil:index')
    if request.method == 'POST':
        pend.jenjang = request.POST.get('jenjang', pend.jenjang)
        pend.institusi = request.POST.get('nama_pt', '').strip()
        pend.prodi_studi = request.POST.get('bidang_ilmu', '').strip()
        pend.tahun_masuk = request.POST.get('tahun_masuk') or None
        pend.tahun_lulus = request.POST.get('tahun_lulus') or None
        pend.no_ijazah = request.POST.get('no_ijazah', '').strip()
        if 'file_ijazah' in request.FILES:
            pend.file_ijazah = compress_uploaded_file(request.FILES['file_ijazah'])
        if 'file_transkrip' in request.FILES:
            pend.file_transkrip = compress_uploaded_file(request.FILES['file_transkrip'])
        pend.save()
        sync_pendidikan_terakhir(pend.dosen)
        messages.success(request, 'Data pendidikan berhasil diupdate.')
    return redirect('profil:index')




# ============================================================
# KUALIFIKASI (Diklat -- Pendidikan Formal & Riwayat Pekerjaan menyusul)
# ============================================================

@login_required
def kualifikasi_index(request):
    user = request.user
    target_user = user

    dosen_id = request.GET.get('dosen_id')
    if dosen_id and user.role in ['admin', 'kaprodi', 'sekprodi', 'operator', 'dekan', 'wadek', 'rektorat', 'biro']:
        target_user = get_object_or_404(User, id=dosen_id)

    tahun_list = TahunAkademik.objects.filter(status='aktif').order_by('-urutan')
    input_terbuka = cek_status_input()
    bisa_edit = user.dapat_kelola(target_user) and input_terbuka

    diklat_list = target_user.diklat_set.all()

    context = {
        'target_user': target_user,
        'tahun_list': tahun_list,
        'bisa_edit': bisa_edit,
        'input_terbuka': input_terbuka,
        'diklat_list': attach_dokumen_count(diklat_list, 'diklat'),
    }
    return render(request, 'profil/kualifikasi.html', context)


@login_required
def tambah_diklat(request):
    if request.method != 'POST':
        return redirect('profil:kualifikasi_index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('profil:kualifikasi_index')

    user = request.user
    dosen_id = request.POST.get('dosen_id')
    target_user, err = resolve_target_user(request, dosen_id)
    if err:
        return err

    diklat = Diklat(
        user=target_user,
        kode_prodi=target_user.kode_prodi or '',
        kode_fakultas=target_user.kode_fakultas or '',
        jenis_diklat=request.POST.get('jenis_diklat', ''),
        nama_diklat=request.POST.get('nama_diklat', '').strip(),
        penyelenggara=request.POST.get('penyelenggara', '').strip(),
        peran=request.POST.get('peran', '').strip(),
        tingkatan=request.POST.get('tingkatan', ''),
        jumlah_jam=request.POST.get('jumlah_jam') or None,
        no_sertifikat=request.POST.get('no_sertifikat', '').strip(),
        tanggal_sertifikat=request.POST.get('tanggal_sertifikat') or None,
        tahun_penyelenggaraan=request.POST.get('tahun_penyelenggaraan') or None,
        tempat=request.POST.get('tempat', '').strip(),
        tanggal_mulai=request.POST.get('tanggal_mulai') or None,
        tanggal_selesai=request.POST.get('tanggal_selesai') or None,
        no_sk_penugasan=request.POST.get('no_sk_penugasan', '').strip(),
        tanggal_sk_penugasan=request.POST.get('tanggal_sk_penugasan') or None,
        semester=request.POST.get('semester', ''),
        tahun_akademik=request.POST.get('tahun_akademik', ''),
        updated_by=user.username,
    )
    diklat.save()
    messages.success(request, 'Data diklat berhasil ditambahkan.')
    return redirect('profil:kualifikasi_index')


@login_required
def hapus_diklat(request, id):
    obj = get_object_or_404(Diklat, id=id)
    if not request.user.dapat_kelola(obj.user):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('profil:kualifikasi_index')
    obj.delete()
    messages.success(request, 'Data diklat berhasil dihapus.')
    return redirect('profil:kualifikasi_index')


@login_required
def edit_diklat(request, id):
    obj = get_object_or_404(Diklat, id=id)
    if not request.user.dapat_kelola(obj.user):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('profil:kualifikasi_index')
    if request.method == 'POST':
        obj.jenis_diklat = request.POST.get('jenis_diklat', obj.jenis_diklat)
        obj.nama_diklat = request.POST.get('nama_diklat', '').strip()
        obj.penyelenggara = request.POST.get('penyelenggara', '').strip()
        obj.peran = request.POST.get('peran', '').strip()
        obj.tingkatan = request.POST.get('tingkatan', obj.tingkatan)
        obj.jumlah_jam = request.POST.get('jumlah_jam') or None
        obj.no_sertifikat = request.POST.get('no_sertifikat', '').strip()
        obj.tanggal_sertifikat = request.POST.get('tanggal_sertifikat') or obj.tanggal_sertifikat
        obj.tahun_penyelenggaraan = request.POST.get('tahun_penyelenggaraan') or obj.tahun_penyelenggaraan
        obj.tempat = request.POST.get('tempat', '').strip()
        obj.tanggal_mulai = request.POST.get('tanggal_mulai') or obj.tanggal_mulai
        obj.tanggal_selesai = request.POST.get('tanggal_selesai') or obj.tanggal_selesai
        obj.no_sk_penugasan = request.POST.get('no_sk_penugasan', '').strip()
        obj.tanggal_sk_penugasan = request.POST.get('tanggal_sk_penugasan') or None
        obj.semester = request.POST.get('semester', '')
        obj.tahun_akademik = request.POST.get('tahun_akademik', obj.tahun_akademik)
        obj.updated_by = request.user.username
        obj.save()
        messages.success(request, 'Data diklat berhasil diupdate.')
    return redirect('profil:kualifikasi_index')


# ============================================================
# KOMPETENSI (Sertifikasi & Tes)
# ============================================================

@login_required
def kompetensi_index(request):
    user = request.user
    target_user = user

    dosen_id = request.GET.get('dosen_id')
    if dosen_id and user.role in ['admin', 'kaprodi', 'sekprodi', 'operator', 'dekan', 'wadek', 'rektorat', 'biro']:
        target_user = get_object_or_404(User, id=dosen_id)

    tahun_list = TahunAkademik.objects.filter(status='aktif').order_by('-urutan')
    input_terbuka = cek_status_input()
    bisa_edit = user.dapat_kelola(target_user) and input_terbuka
    bisa_validasi = user.role in Sertifikasi.ROLE_BOLEH_VALIDASI

    context = {
        'target_user': target_user,
        'tahun_list': tahun_list,
        'bisa_edit': bisa_edit,
        'bisa_validasi': bisa_validasi,
        'input_terbuka': input_terbuka,
        'sertifikasi_list': attach_dokumen_count(target_user.sertifikasi_set.all(), 'sertifikasi'),
        'tes_list': attach_dokumen_count(target_user.tes_set.all(), 'tes'),
    }
    return render(request, 'profil/kompetensi.html', context)


@login_required
def tambah_sertifikasi(request):
    if request.method != 'POST':
        return redirect('profil:kompetensi_index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('profil:kompetensi_index')

    user = request.user
    dosen_id = request.POST.get('dosen_id')
    target_user, err = resolve_target_user(request, dosen_id)
    if err:
        return err

    jenis = request.POST.get('jenis_sertifikasi', '')
    Sertifikasi.objects.create(
        user=target_user,
        kode_prodi=target_user.kode_prodi or '',
        kode_fakultas=target_user.kode_fakultas or '',
        jenis_sertifikasi=jenis,
        bidang_studi=request.POST.get('bidang_studi', '').strip(),
        lembaga_sertifikasi=request.POST.get('lembaga_sertifikasi', '').strip(),
        no_registrasi_pendidik=request.POST.get('no_registrasi_pendidik', '').strip(),
        no_peserta=request.POST.get('no_peserta', '').strip(),
        no_sk_sertifikasi=request.POST.get('no_sk_sertifikasi', '').strip(),
        tahun_sertifikasi=request.POST.get('tahun_sertifikasi') or None,
        tmt_sertifikasi=request.POST.get('tmt_sertifikasi') or None,
        tst_sertifikasi=request.POST.get('tst_sertifikasi') or None,
        # Serdos butuh validasi kaprodi/dekan; Kompetensi/Profesi langsung aktif.
        status_validasi='menunggu' if jenis == 'serdos' else 'disetujui',
        semester=request.POST.get('semester', ''),
        tahun_akademik=request.POST.get('tahun_akademik', ''),
        updated_by=user.username,
    )
    messages.success(request, 'Data sertifikasi berhasil ditambahkan.')
    return redirect('profil:kompetensi_index')


@login_required
def hapus_sertifikasi(request, id):
    obj = get_object_or_404(Sertifikasi, id=id)
    if not request.user.dapat_kelola(obj.user):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('profil:kompetensi_index')
    obj.delete()
    messages.success(request, 'Data sertifikasi berhasil dihapus.')
    return redirect('profil:kompetensi_index')


@login_required
def edit_sertifikasi(request, id):
    obj = get_object_or_404(Sertifikasi, id=id)
    if not request.user.dapat_kelola(obj.user):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('profil:kompetensi_index')
    if request.method == 'POST':
        obj.jenis_sertifikasi = request.POST.get('jenis_sertifikasi', obj.jenis_sertifikasi)
        obj.bidang_studi = request.POST.get('bidang_studi', '').strip()
        obj.lembaga_sertifikasi = request.POST.get('lembaga_sertifikasi', '').strip()
        obj.no_registrasi_pendidik = request.POST.get('no_registrasi_pendidik', '').strip()
        obj.no_peserta = request.POST.get('no_peserta', '').strip()
        obj.no_sk_sertifikasi = request.POST.get('no_sk_sertifikasi', '').strip()
        obj.tahun_sertifikasi = request.POST.get('tahun_sertifikasi') or obj.tahun_sertifikasi
        obj.tmt_sertifikasi = request.POST.get('tmt_sertifikasi') or None
        obj.tst_sertifikasi = request.POST.get('tst_sertifikasi') or None
        obj.semester = request.POST.get('semester', '')
        obj.tahun_akademik = request.POST.get('tahun_akademik', obj.tahun_akademik)
        obj.updated_by = request.user.username
        # Cuma role tertentu yang boleh validasi Sertifikasi Dosen (Serdos) --
        # dosen pemilik tidak bisa menyetujui sertifikasinya sendiri.
        if request.user.role in Sertifikasi.ROLE_BOLEH_VALIDASI:
            obj.status_validasi = request.POST.get('status_validasi', obj.status_validasi)
        obj.save()
        messages.success(request, 'Data sertifikasi berhasil diupdate.')
    return redirect('profil:kompetensi_index')


@login_required
def tambah_tes(request):
    if request.method != 'POST':
        return redirect('profil:kompetensi_index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('profil:kompetensi_index')

    user = request.user
    dosen_id = request.POST.get('dosen_id')
    target_user, err = resolve_target_user(request, dosen_id)
    if err:
        return err

    TesKompetensi.objects.create(
        user=target_user,
        kode_prodi=target_user.kode_prodi or '',
        kode_fakultas=target_user.kode_fakultas or '',
        jenis_tes=request.POST.get('jenis_tes', ''),
        nama_tes=request.POST.get('nama_tes', '').strip(),
        penyelenggara=request.POST.get('penyelenggara', '').strip(),
        tanggal_tes=request.POST.get('tanggal_tes') or None,
        tahun=request.POST.get('tahun') or None,
        skor_tes=request.POST.get('skor_tes') or None,
        semester=request.POST.get('semester', ''),
        tahun_akademik=request.POST.get('tahun_akademik', ''),
        updated_by=user.username,
    )
    messages.success(request, 'Data tes berhasil ditambahkan.')
    return redirect('profil:kompetensi_index')


@login_required
def hapus_tes(request, id):
    obj = get_object_or_404(TesKompetensi, id=id)
    if not request.user.dapat_kelola(obj.user):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('profil:kompetensi_index')
    obj.delete()
    messages.success(request, 'Data tes berhasil dihapus.')
    return redirect('profil:kompetensi_index')


@login_required
def edit_tes(request, id):
    obj = get_object_or_404(TesKompetensi, id=id)
    if not request.user.dapat_kelola(obj.user):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('profil:kompetensi_index')
    if request.method == 'POST':
        obj.jenis_tes = request.POST.get('jenis_tes', obj.jenis_tes)
        obj.nama_tes = request.POST.get('nama_tes', '').strip()
        obj.penyelenggara = request.POST.get('penyelenggara', '').strip()
        obj.tanggal_tes = request.POST.get('tanggal_tes') or obj.tanggal_tes
        obj.tahun = request.POST.get('tahun') or obj.tahun
        obj.skor_tes = request.POST.get('skor_tes') or obj.skor_tes
        obj.semester = request.POST.get('semester', '')
        obj.tahun_akademik = request.POST.get('tahun_akademik', obj.tahun_akademik)
        obj.updated_by = request.user.username
        obj.save()
        messages.success(request, 'Data tes berhasil diupdate.')
    return redirect('profil:kompetensi_index')


# ============================================================
# DATA DOKUMEN -- menu "Data Dokumen" (SISTER: Riwayat Dokumen Pribadi).
# Gabungan: DokumenLain (CRUD bebas, lokal SIKD) + dokumen yang sudah
# tersimpan di SIMDA lewat tab Profil/Kualifikasi (KTP/NPWP/SK Pengangkatan
# di DataDosen, SK Jabfung per riwayat, Ijazah/Transkrip per riwayat
# pendidikan) -- yang terakhir ini read-only di sini, tetap diedit dari
# tab asalnya supaya tidak ada dua tempat mengubah data yang sama.
# ============================================================

def _dokumen_target_user(request):
    user = request.user
    dosen_id = request.GET.get('dosen_id')
    if dosen_id and user.role in ['admin', 'kaprodi', 'sekprodi', 'operator', 'dekan', 'wadek', 'rektorat', 'biro']:
        return get_object_or_404(User, id=dosen_id)
    return user


@login_required
def dokumen_index(request):
    user = request.user
    target_user = _dokumen_target_user(request)
    input_terbuka = cek_status_input()
    bisa_edit = user.dapat_kelola(target_user) and input_terbuka

    dokumen_lain_list = target_user.dokumen_set.all().order_by('-tgl_input')

    dokumen_gabungan = []
    for d in dokumen_lain_list:
        dokumen_gabungan.append({
            'sumber': 'lokal',
            'id': d.id,
            'nama': d.nama_dokumen,
            'jenis': d.get_jenis_dokumen_display(),
            'jenis_raw': d.jenis_dokumen,
            'no_dokumen': d.no_dokumen,
            'tanggal': d.tgl_terbit,
            'file_url': d.file_dokumen.url if d.file_dokumen else '',
            'link': d.link_dokumen,
            'keterangan': d.keterangan,
        })

    profil = get_simda_dosen_or_none(target_user)
    if profil:
        if profil.foto:
            dokumen_gabungan.append({
                'sumber': 'profil', 'id': None, 'nama': 'Foto Profil',
                'jenis': 'Foto Profil', 'tanggal': None,
                'file_url': profil.foto.url, 'link': '',
            })
        if profil.file_ktp:
            dokumen_gabungan.append({
                'sumber': 'profil', 'id': None, 'nama': 'KTP',
                'jenis': 'KTP', 'tanggal': None,
                'file_url': profil.file_ktp.url, 'link': '',
            })
        if profil.file_npwp:
            dokumen_gabungan.append({
                'sumber': 'profil', 'id': None, 'nama': 'NPWP',
                'jenis': 'NPWP', 'tanggal': None,
                'file_url': profil.file_npwp.url, 'link': '',
            })
        if profil.file_sk_pengangkatan:
            dokumen_gabungan.append({
                'sumber': 'profil', 'id': None, 'nama': 'SK Pengangkatan',
                'jenis': 'SK Pengangkatan', 'tanggal': None,
                'file_url': profil.file_sk_pengangkatan.url, 'link': '',
            })
        for jf in profil.riwayat_jabfung.all():
            if jf.file_sk:
                dokumen_gabungan.append({
                    'sumber': 'jabfung', 'id': None,
                    'nama': f'SK Jabatan Fungsional (TMT {jf.tmt})' if jf.tmt else 'SK Jabatan Fungsional',
                    'jenis': 'SK Jabatan Fungsional', 'tanggal': jf.tmt,
                    'file_url': jf.file_sk.url, 'link': '',
                })
        for pg in profil.riwayat_pangkat_golongan.all():
            if pg.file_sk:
                dokumen_gabungan.append({
                    'sumber': 'pangkat', 'id': None,
                    'nama': f'SK Inpassing {pg.golongan_display} (TMT {pg.tmt})' if pg.tmt else f'SK Inpassing {pg.golongan_display}',
                    'jenis': 'SK Pangkat/Inpassing', 'tanggal': pg.tmt,
                    'file_url': pg.file_sk.url, 'link': '',
                })
        for rp in profil.riwayat_pendidikan.all():
            if rp.file_ijazah:
                dokumen_gabungan.append({
                    'sumber': 'pendidikan', 'id': None,
                    'nama': f'Ijazah {rp.jenjang}', 'jenis': 'Ijazah',
                    'tanggal': None, 'file_url': rp.file_ijazah.url, 'link': '',
                })
            if rp.file_transkrip:
                dokumen_gabungan.append({
                    'sumber': 'pendidikan', 'id': None,
                    'nama': f'Transkrip {rp.jenjang}', 'jenis': 'Transkrip',
                    'tanggal': None, 'file_url': rp.file_transkrip.url, 'link': '',
                })

    context = {
        'target_user': target_user,
        'bisa_edit': bisa_edit,
        'input_terbuka': input_terbuka,
        'dokumen_gabungan': dokumen_gabungan,
        'jenis_dokumen_choices': DokumenLain.JENIS_DOKUMEN,
    }
    return render(request, 'profil/dokumen.html', context)


@login_required
def tambah_dokumen_lain(request):
    if request.method != 'POST':
        return redirect('profil:dokumen_index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('profil:dokumen_index')

    dosen_id = request.POST.get('dosen_id')
    if dosen_id and request.user.role in ['admin', 'kaprodi', 'sekprodi', 'operator', 'dekan', 'wadek', 'rektorat', 'biro']:
        target_user = get_object_or_404(User, id=dosen_id)
    else:
        target_user = request.user

    if not request.user.dapat_kelola(target_user):
        messages.error(request, 'Tidak memiliki akses untuk mengelola data dosen ini.')
        return redirect('profil:dokumen_index')

    dok = DokumenLain(
        user=target_user,
        jenis_dokumen=request.POST.get('jenis_dokumen', ''),
        nama_dokumen=request.POST.get('nama_dokumen', '').strip(),
        no_dokumen=request.POST.get('no_dokumen', '').strip(),
        tgl_terbit=request.POST.get('tgl_terbit') or None,
        keterangan=request.POST.get('keterangan', '').strip(),
        link_dokumen=request.POST.get('link_dokumen', '').strip() or None,
        updated_by=request.user.username,
    )
    if 'file_dokumen' in request.FILES:
        dok.file_dokumen = compress_uploaded_file(request.FILES['file_dokumen'])
    dok.save()
    messages.success(request, 'Dokumen berhasil ditambahkan.')
    return redirect('profil:dokumen_index')


@login_required
def edit_dokumen_lain(request, id):
    obj = get_object_or_404(DokumenLain, id=id)
    if not request.user.dapat_kelola(obj.user):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('profil:dokumen_index')
    if request.method == 'POST':
        obj.jenis_dokumen = request.POST.get('jenis_dokumen', obj.jenis_dokumen)
        obj.nama_dokumen = request.POST.get('nama_dokumen', '').strip()
        obj.no_dokumen = request.POST.get('no_dokumen', '').strip()
        obj.tgl_terbit = request.POST.get('tgl_terbit') or None
        obj.keterangan = request.POST.get('keterangan', '').strip()
        obj.link_dokumen = request.POST.get('link_dokumen', '').strip() or None
        if 'file_dokumen' in request.FILES:
            obj.file_dokumen = compress_uploaded_file(request.FILES['file_dokumen'])
        obj.updated_by = request.user.username
        obj.save()
        messages.success(request, 'Dokumen berhasil diupdate.')
    return redirect('profil:dokumen_index')


@login_required
def hapus_dokumen_lain(request, id):
    obj = get_object_or_404(DokumenLain, id=id)
    if not request.user.dapat_kelola(obj.user):
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('profil:dokumen_index')
    obj.delete()
    messages.success(request, 'Dokumen berhasil dihapus.')
    return redirect('profil:dokumen_index')
