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

from .models import BKD, Penelitian, Publikasi, PKM, HKI, DokumenKinerja
from django.core.exceptions import ValidationError
import os

def validate_dokumen(file):
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ['.pdf', '.jpg', '.jpeg', '.png']:
        raise ValidationError('Hanya PDF, JPG, PNG yang diizinkan.')
    if file.size > 5 * 1024 * 1024:
        raise ValidationError('Ukuran file maksimal 5MB.')


@login_required
def kelola_dokumen(request, jenis_kinerja, kinerja_id):
    user = request.user

    # Validasi akses dan ambil objek kinerja
    KINERJA_MAP = {
        'penelitian': Penelitian,
        'publikasi': Publikasi,
        'pkm': PKM,
        'hki': HKI,
        'bkd': BKD,
    }

    if jenis_kinerja not in KINERJA_MAP:
        messages.error(request, 'Jenis kinerja tidak valid.')
        return redirect('kinerja:index')

    Model = KINERJA_MAP[jenis_kinerja]
    kinerja_obj = get_object_or_404(Model, id=kinerja_id)

    # Cek kepemilikan
    if kinerja_obj.user != user and user.role not in ['admin', 'operator']:
        messages.error(request, 'Anda tidak memiliki akses.')
        return redirect('kinerja:index')

    dokumen_list = DokumenKinerja.objects.filter(
        user=kinerja_obj.user,
        jenis_kinerja=jenis_kinerja,
        kinerja_id=kinerja_id
    ).order_by('jenis_dokumen')

    if request.method == 'POST':
        aksi = request.POST.get('aksi')

        if aksi == 'tambah':
            jenis_dok = request.POST.get('jenis_dokumen', '')
            nama_dok = request.POST.get('nama_dokumen', '').strip()
            keterangan = request.POST.get('keterangan', '').strip()
            link_dok = request.POST.get('link_dokumen', '').strip()

            if not nama_dok:
                messages.error(request, 'Nama dokumen wajib diisi.')
            else:
                dok = DokumenKinerja(
                    user=kinerja_obj.user,
                    jenis_kinerja=jenis_kinerja,
                    kinerja_id=kinerja_id,
                    jenis_dokumen=jenis_dok,
                    nama_dokumen=nama_dok,
                    keterangan=keterangan,
                    link_dokumen=link_dok or None,
                    updated_by=user.username
                )
                if 'file_dokumen' in request.FILES:
                    file = request.FILES['file_dokumen']
                    try:
                        validate_dokumen(file)
                        dok.file_dokumen = file
                    except ValidationError as e:
                        messages.error(request, str(e.message))
                        return redirect('kinerja:kelola_dokumen', jenis_kinerja=jenis_kinerja, kinerja_id=kinerja_id)
                dok.save()
                messages.success(request, f'Dokumen "{nama_dok}" berhasil ditambahkan.')

        elif aksi == 'hapus':
            dok_id = request.POST.get('dok_id')
            dok = get_object_or_404(DokumenKinerja, id=dok_id)
            if dok.user == kinerja_obj.user or user.role in ['admin', 'operator']:
                nama = dok.nama_dokumen
                dok.delete()
                messages.success(request, f'Dokumen "{nama}" berhasil dihapus.')
        elif aksi == 'edit':
            dok_id = request.POST.get('dok_id')
            dok = get_object_or_404(DokumenKinerja, id=dok_id)
            if dok.user == kinerja_obj.user or user.role in ['admin', 'operator']:
                dok.jenis_dokumen = request.POST.get('jenis_dokumen', dok.jenis_dokumen)
                dok.nama_dokumen = request.POST.get('nama_dokumen', '').strip() or dok.nama_dokumen
                dok.keterangan = request.POST.get('keterangan', '').strip()
                dok.link_dokumen = request.POST.get('link_dokumen', '').strip() or None
                dok.updated_by = user.username
                if 'file_dokumen' in request.FILES:
                    file = request.FILES['file_dokumen']
                    try:
                        validate_dokumen(file)
                        dok.file_dokumen = file
                    except ValidationError as e:
                        messages.error(request, str(e.message))
                        return redirect('kinerja:kelola_dokumen',
                            jenis_kinerja=jenis_kinerja, kinerja_id=kinerja_id)
                dok.save()
                messages.success(request, f'Dokumen "{dok.nama_dokumen}" berhasil diupdate.')        

        return redirect('kinerja:kelola_dokumen', jenis_kinerja=jenis_kinerja, kinerja_id=kinerja_id)

    # Judul kinerja
    if hasattr(kinerja_obj, 'judul'):
        judul_kinerja = kinerja_obj.judul[:80]
    else:
        judul_kinerja = f'BKD {kinerja_obj.semester} {kinerja_obj.tahun_akademik}'

    context = {
        'kinerja_obj': kinerja_obj,
        'jenis_kinerja': jenis_kinerja,
        'kinerja_id': kinerja_id,
        'judul_kinerja': judul_kinerja,
        'dokumen_list': dokumen_list,
        'jenis_dokumen_choices': DokumenKinerja.JENIS_DOKUMEN,
    }
    return render(request, 'kinerja/kelola_dokumen.html', context)

@login_required
def edit_bkd(request, id):
    obj = get_object_or_404(BKD, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('kinerja:index')
    if request.method == 'POST':
        obj.semester = request.POST.get('semester', obj.semester)
        obj.tahun_akademik = request.POST.get('tahun_akademik', obj.tahun_akademik)
        obj.link_bkd = request.POST.get('link_bkd', '').strip() or None
        obj.keterangan = request.POST.get('keterangan', '').strip()
        obj.updated_by = request.user.username
        if 'file_bkd' in request.FILES:
            obj.file_bkd = request.FILES['file_bkd']
        obj.save()
        messages.success(request, 'BKD berhasil diupdate.')
    return redirect('kinerja:index')


@login_required
def edit_penelitian(request, id):
    obj = get_object_or_404(Penelitian, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('kinerja:index')
    if request.method == 'POST':
        obj.judul = request.POST.get('judul', '').strip()
        obj.semester = request.POST.get('semester', '')
        obj.tahun_akademik = request.POST.get('tahun_akademik', obj.tahun_akademik)
        obj.jml_mahasiswa = request.POST.get('jml_mahasiswa', 0)
        obj.ln_i = request.POST.get('ln_i', '')
        obj.jenis_hibah = request.POST.get('jenis_hibah', '').strip()
        obj.sumber = request.POST.get('sumber', '').strip()
        obj.durasi = request.POST.get('durasi', 1)
        obj.pendanaan = request.POST.get('pendanaan', 0) or 0
        obj.link_bukti = request.POST.get('link_bukti', '').strip() or None
        obj.updated_by = request.user.username
        obj.save()
        messages.success(request, 'Penelitian berhasil diupdate.')
    return redirect('kinerja:index')


@login_required
def edit_publikasi(request, id):
    obj = get_object_or_404(Publikasi, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('kinerja:index')
    if request.method == 'POST':
        obj.judul = request.POST.get('judul', '').strip()
        obj.jenis_publikasi = request.POST.get('jenis_publikasi', obj.jenis_publikasi)
        obj.nama_jurnal = request.POST.get('nama_jurnal', '').strip()
        obj.volume = request.POST.get('volume', '').strip()
        obj.nomor = request.POST.get('nomor', '').strip()
        obj.halaman = request.POST.get('halaman', '').strip()
        obj.tahun_terbit = request.POST.get('tahun_terbit') or None
        obj.semester = request.POST.get('semester', '')
        obj.tahun_akademik = request.POST.get('tahun_akademik', obj.tahun_akademik)
        obj.link_bukti = request.POST.get('link_bukti', '').strip() or None
        obj.updated_by = request.user.username
        obj.save()
        messages.success(request, 'Publikasi berhasil diupdate.')
    return redirect('kinerja:index')


@login_required
def edit_pkm(request, id):
    obj = get_object_or_404(PKM, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('kinerja:index')
    if request.method == 'POST':
        obj.judul = request.POST.get('judul', '').strip()
        obj.semester = request.POST.get('semester', '')
        obj.tahun_akademik = request.POST.get('tahun_akademik', obj.tahun_akademik)
        obj.jml_mahasiswa = request.POST.get('jml_mahasiswa', 0)
        obj.ln_i = request.POST.get('ln_i', '')
        obj.jenis_hibah = request.POST.get('jenis_hibah', '').strip()
        obj.sumber = request.POST.get('sumber', '').strip()
        obj.durasi = request.POST.get('durasi', 1)
        obj.pendanaan = request.POST.get('pendanaan', 0) or 0
        obj.link_bukti = request.POST.get('link_bukti', '').strip() or None
        obj.updated_by = request.user.username
        obj.save()
        messages.success(request, 'PKM berhasil diupdate.')
    return redirect('kinerja:index')


@login_required
def edit_hki(request, id):
    obj = get_object_or_404(HKI, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('kinerja:index')
    if request.method == 'POST':
        obj.judul = request.POST.get('judul', '').strip()
        obj.jenis_hki = request.POST.get('jenis_hki', obj.jenis_hki)
        obj.no_hki = request.POST.get('no_hki', '').strip()
        obj.tahun_perolehan = request.POST.get('tahun_perolehan') or None
        obj.semester = request.POST.get('semester', '')
        obj.tahun_akademik = request.POST.get('tahun_akademik', obj.tahun_akademik)
        obj.link_bukti = request.POST.get('link_bukti', '').strip() or None
        obj.updated_by = request.user.username
        obj.save()
        messages.success(request, 'HKI berhasil diupdate.')
    return redirect('kinerja:index')