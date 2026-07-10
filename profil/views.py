from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from master.models import TahunAkademik, Pengaturan
from accounts.models import User
from simda_dosen.models import (
    DataDosen, RiwayatJabatanFungsional, RiwayatPendidikanDosen,
    AgamaPublik, JabatanFungsionalPublik,
)
from simda_dosen.utils import get_simda_dosen_or_none
from .models import Sertifikat, DokumenLain

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

    profil = get_simda_dosen_or_none(target_user)

    if profil:
        jabfung_list = profil.riwayat_jabfung.all().order_by('-tmt')
        pendidikan_list = profil.riwayat_pendidikan.all().order_by('-tahun_lulus')
    else:
        jabfung_list = RiwayatJabatanFungsional.objects.none()
        pendidikan_list = RiwayatPendidikanDosen.objects.none()

    sertifikat_list = target_user.sertifikat_set.all().order_by('-tahun_terbit')
    dokumen_list = target_user.dokumen_set.all().order_by('-tgl_input')
    tahun_list = TahunAkademik.objects.filter(status='aktif').order_by('-urutan')
    input_terbuka = cek_status_input()
    bisa_edit = (user == target_user or user.role in ['admin', 'operator']) and input_terbuka

    context = {
        'target_user': target_user,
        'profil': profil,
        'jabfung_list': jabfung_list,
        'pendidikan_list': pendidikan_list,
        'sertifikat_list': sertifikat_list,
        'dokumen_list': dokumen_list,
        'tahun_list': tahun_list,
        'bisa_edit': bisa_edit,
        'input_terbuka': input_terbuka,
        'agama_list': AgamaPublik.objects.using('simda').all(),
        'jabfung_ref_list': JabatanFungsionalPublik.objects.using('simda').all(),
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
    if dosen_id and user.role in ['admin', 'operator']:
        target_user = get_object_or_404(User, id=dosen_id)
    else:
        target_user = user

    profil = get_simda_dosen_or_none(target_user)
    if not profil:
        messages.error(request, 'NIDN Anda belum cocok dengan data di SIMDA. Hubungi admin untuk membetulkan NIDN.')
        return redirect('profil:index')

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

    if 'foto' in request.FILES:
        profil.foto = request.FILES['foto']
    if 'file_ktp' in request.FILES:
        profil.file_ktp = request.FILES['file_ktp']
    if 'file_npwp' in request.FILES:
        profil.file_npwp = request.FILES['file_npwp']

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
    target_user = get_object_or_404(User, id=dosen_id) if dosen_id and user.role in ['admin', 'operator'] else user
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
        tgl_selesai=request.POST.get('tgl_selesai') or None,
        url_sk=request.POST.get('url_sk', '').strip(),
        keterangan=request.POST.get('keterangan', '').strip(),
    )
    if 'file_sk' in request.FILES:
        jabfung.file_sk = request.FILES['file_sk']
    jabfung.save()

    messages.success(request, 'Riwayat jabatan fungsional berhasil ditambahkan ke SIMDA.')
    return redirect('profil:index')

@login_required
def hapus_jabfung(request, jabfung_id):
    jabfung = get_object_or_404(RiwayatJabatanFungsional, id=jabfung_id)
    if request.user.nidn != jabfung.dosen.nidn and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('profil:index')
    jabfung.delete()
    messages.success(request, 'Data jabatan berhasil dihapus.')
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
    target_user = get_object_or_404(User, id=dosen_id) if dosen_id and user.role in ['admin', 'operator'] else user
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
        pend.file_ijazah = request.FILES['file_ijazah']
    if 'file_transkrip' in request.FILES:
        pend.file_transkrip = request.FILES['file_transkrip']
    pend.save()
    messages.success(request, 'Data pendidikan berhasil ditambahkan ke SIMDA.')
    return redirect('profil:index')

@login_required
def hapus_pendidikan(request, pend_id):
    pend = get_object_or_404(RiwayatPendidikanDosen, id=pend_id)
    if request.user.nidn != pend.dosen.nidn and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('profil:index')
    pend.delete()
    messages.success(request, 'Data pendidikan berhasil dihapus.')
    return redirect('profil:index')

@login_required
def tambah_sertifikat(request):
    if request.method != 'POST':
        return redirect('profil:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('profil:index')

    user = request.user
    dosen_id = request.POST.get('dosen_id')
    target_user = get_object_or_404(User, id=dosen_id) if dosen_id and user.role in ['admin', 'operator'] else user

    sert = Sertifikat(
        user=target_user,
        jenis_sertifikat=request.POST.get('jenis_sertifikat', ''),
        nama_sertifikat=request.POST.get('nama_sertifikat', '').strip(),
        no_sertifikat=request.POST.get('no_sertifikat', '').strip(),
        lembaga_penerbit=request.POST.get('lembaga_penerbit', '').strip(),
        tahun_terbit=request.POST.get('tahun_terbit') or None,
        masa_berlaku=request.POST.get('masa_berlaku', '').strip(),
        updated_by=user.username
    )
    if 'file_sertifikat' in request.FILES:
        sert.file_sertifikat = request.FILES['file_sertifikat']
    sert.save()
    messages.success(request, 'Sertifikat berhasil ditambahkan.')
    return redirect('profil:index')

@login_required
def hapus_sertifikat(request, sert_id):
    sert = get_object_or_404(Sertifikat, id=sert_id)
    if request.user != sert.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('profil:index')
    sert.delete()
    messages.success(request, 'Sertifikat berhasil dihapus.')
    return redirect('profil:index')

@login_required
def edit_jabfung(request, jabfung_id):
    jabfung = get_object_or_404(RiwayatJabatanFungsional, id=jabfung_id)
    if request.user.nidn != jabfung.dosen.nidn and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('profil:index')
    if request.method == 'POST':
        jabfung.jabatan_fungsional_id = request.POST.get('jabatan_fungsional_id') or jabfung.jabatan_fungsional_id
        jabfung.no_sk = request.POST.get('no_sk', '').strip()
        jabfung.tgl_sk = request.POST.get('tgl_sk') or None
        jabfung.tmt = request.POST.get('tmt') or None
        jabfung.tgl_selesai = request.POST.get('tgl_selesai') or None
        jabfung.url_sk = request.POST.get('url_sk', '').strip()
        jabfung.keterangan = request.POST.get('keterangan', '').strip()
        if 'file_sk' in request.FILES:
            jabfung.file_sk = request.FILES['file_sk']
        jabfung.save()
        messages.success(request, 'Data jabatan berhasil diupdate.')
    return redirect('profil:index')


@login_required
def edit_pendidikan(request, pend_id):
    pend = get_object_or_404(RiwayatPendidikanDosen, id=pend_id)
    if request.user.nidn != pend.dosen.nidn and request.user.role not in ['admin', 'operator']:
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
            pend.file_ijazah = request.FILES['file_ijazah']
        if 'file_transkrip' in request.FILES:
            pend.file_transkrip = request.FILES['file_transkrip']
        pend.save()
        messages.success(request, 'Data pendidikan berhasil diupdate.')
    return redirect('profil:index')


@login_required
def edit_sertifikat(request, sert_id):
    sert = get_object_or_404(Sertifikat, id=sert_id)
    if request.user != sert.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('profil:index')
    if request.method == 'POST':
        sert.jenis_sertifikat = request.POST.get('jenis_sertifikat', sert.jenis_sertifikat)
        sert.nama_sertifikat = request.POST.get('nama_sertifikat', '').strip()
        sert.no_sertifikat = request.POST.get('no_sertifikat', '').strip()
        sert.lembaga_penerbit = request.POST.get('lembaga_penerbit', '').strip()
        sert.tahun_terbit = request.POST.get('tahun_terbit') or None
        sert.masa_berlaku = request.POST.get('masa_berlaku', '').strip()
        sert.updated_by = request.user.username
        if 'file_sertifikat' in request.FILES:
            sert.file_sertifikat = request.FILES['file_sertifikat']
        sert.save()
        messages.success(request, 'Sertifikat berhasil diupdate.')
    return redirect('profil:index')
