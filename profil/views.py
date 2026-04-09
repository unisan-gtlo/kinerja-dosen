from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from master.models import TahunAkademik, Pengaturan
from accounts.models import User
from .models import ProfilDosen, RiwayatJabfung, RiwayatPendidikan, Sertifikat, DokumenLain

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

    try:
        profil = target_user.profil
    except ProfilDosen.DoesNotExist:
        profil = None

    jabfung_list = target_user.jabfung_set.all().order_by('-tgl_sk')
    pendidikan_list = target_user.pendidikan_set.all().order_by('-tahun_lulus')
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

    profil, created = ProfilDosen.objects.get_or_create(user=target_user)
    profil.nik = request.POST.get('nik', '').strip()
    profil.tempat_lahir = request.POST.get('tempat_lahir', '').strip()
    profil.tgl_lahir = request.POST.get('tgl_lahir') or None
    profil.jenis_kelamin = request.POST.get('jenis_kelamin', '')
    profil.agama = request.POST.get('agama', '')
    profil.status_pernikahan = request.POST.get('status_pernikahan', '')
    profil.alamat = request.POST.get('alamat', '').strip()
    profil.email_pribadi = request.POST.get('email_pribadi', '').strip()
    profil.jabfung_aktif = request.POST.get('jabfung_aktif', '')
    profil.pendidikan_terakhir = request.POST.get('pendidikan_terakhir', '')
    profil.bidang_keahlian = request.POST.get('bidang_keahlian', '').strip()
    profil.mata_kuliah_diampu = request.POST.get('mata_kuliah_diampu', '').strip()
    profil.link_dokumen_lain = request.POST.get('link_dokumen_lain', '').strip()
    profil.updated_by = user.username

    if 'foto' in request.FILES:
        profil.foto = request.FILES['foto']
    if 'file_ktp' in request.FILES:
        profil.file_ktp = request.FILES['file_ktp']
    if 'file_npwp' in request.FILES:
        profil.file_npwp = request.FILES['file_npwp']
    if 'file_sk_yayasan' in request.FILES:
        profil.file_sk_yayasan = request.FILES['file_sk_yayasan']

    profil.save()
    messages.success(request, 'Profil berhasil disimpan.')
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

    jabfung = RiwayatJabfung(
        user=target_user,
        jabatan=request.POST.get('jabatan', ''),
        no_sk=request.POST.get('no_sk', '').strip(),
        tgl_sk=request.POST.get('tgl_sk') or None,
        tmt_berlaku=request.POST.get('tmt_berlaku') or None,
        instansi_penerbit=request.POST.get('instansi_penerbit', '').strip(),
        link_sk=request.POST.get('link_sk', '').strip(),
        status=request.POST.get('status', 'aktif'),
        updated_by=user.username
    )
    if 'file_sk' in request.FILES:
        jabfung.file_sk = request.FILES['file_sk']
    jabfung.save()

    if jabfung.status == 'aktif':
        try:
            profil = target_user.profil
            profil.jabfung_aktif = jabfung.jabatan
            profil.save()
        except:
            pass

    messages.success(request, f'Jabatan "{jabfung.jabatan}" berhasil ditambahkan.')
    return redirect('profil:index')

@login_required
def hapus_jabfung(request, jabfung_id):
    jabfung = get_object_or_404(RiwayatJabfung, id=jabfung_id)
    if request.user != jabfung.user and request.user.role not in ['admin', 'operator']:
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

    pend = RiwayatPendidikan(
        user=target_user,
        jenjang=request.POST.get('jenjang', ''),
        bidang_ilmu=request.POST.get('bidang_ilmu', '').strip(),
        nama_pt=request.POST.get('nama_pt', '').strip(),
        kota_pt=request.POST.get('kota_pt', '').strip(),
        negara=request.POST.get('negara', 'Indonesia').strip(),
        tahun_masuk=request.POST.get('tahun_masuk') or None,
        tahun_lulus=request.POST.get('tahun_lulus') or None,
        no_ijazah=request.POST.get('no_ijazah', '').strip(),
        updated_by=user.username
    )
    if 'file_ijazah' in request.FILES:
        pend.file_ijazah = request.FILES['file_ijazah']
    if 'file_transkrip' in request.FILES:
        pend.file_transkrip = request.FILES['file_transkrip']
    pend.save()
    messages.success(request, 'Data pendidikan berhasil ditambahkan.')
    return redirect('profil:index')

@login_required
def hapus_pendidikan(request, pend_id):
    pend = get_object_or_404(RiwayatPendidikan, id=pend_id)
    if request.user != pend.user and request.user.role not in ['admin', 'operator']:
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