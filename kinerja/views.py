from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from master.models import TahunAkademik, Pengaturan
from accounts.models import User
from simda_dosen.models import RiwayatBKD, TahunAkademikPublik
from simda_dosen.utils import get_simda_dosen_or_none
from profil.models import Diklat, Sertifikasi, TesKompetensi
from pendidikan.models import (
    Pengajaran, BimbinganMahasiswa, PengujianMahasiswa, BahanAjar,
    PembinaanMahasiswa, OrasiIlmiah, TugasTambahan,
)
from penelitian.models import Penelitian, PublikasiKarya, PatenHki
from .models import PKM, Penghargaan, KegiatanPenunjang, DokumenKinerja
from .utils import attach_dokumen_count

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

    pkm_list = target_user.pkm_set.all()
    penghargaan_list = target_user.penghargaan_set.all()
    penunjang_list = target_user.penunjang_set.all()

    if filter_tahun:
        pkm_list = pkm_list.filter(tahun_akademik=filter_tahun)
        penghargaan_list = penghargaan_list.filter(tahun_akademik=filter_tahun)
        penunjang_list = penunjang_list.filter(tahun_akademik=filter_tahun)

    if filter_semester:
        pkm_list = pkm_list.filter(semester=filter_semester)
        penghargaan_list = penghargaan_list.filter(semester=filter_semester)
        penunjang_list = penunjang_list.filter(semester=filter_semester)

    context = {
        'target_user': target_user,
        'tahun_list': tahun_list,
        'bisa_edit': bisa_edit,
        'input_terbuka': input_terbuka,
        'filter_tahun': filter_tahun,
        'filter_semester': filter_semester,
        'pkm_list': attach_dokumen_count(pkm_list, 'pkm'),
        'penghargaan_list': attach_dokumen_count(penghargaan_list, 'penghargaan'),
        'penunjang_list': attach_dokumen_count(penunjang_list, 'penunjang'),
    }
    return render(request, 'kinerja/index.html', context)


@login_required
def bkd_index(request):
    user = request.user
    target_user = user

    dosen_id = request.GET.get('dosen_id')
    if dosen_id and user.role in ['admin', 'kaprodi', 'sekprodi', 'operator', 'dekan', 'wadek', 'rektorat', 'biro']:
        target_user = get_object_or_404(User, id=dosen_id)

    tahun_list = TahunAkademik.objects.filter(status='aktif').order_by('-urutan')
    input_terbuka = cek_status_input()
    bisa_edit = (user == target_user or user.role in ['admin', 'operator']) and input_terbuka

    filter_tahun = request.GET.get('tahun', '')
    filter_semester = request.GET.get('semester', '')

    dosen = get_simda_dosen_or_none(target_user)
    bkd_list = dosen.riwayat_bkd.all() if dosen else RiwayatBKD.objects.none()

    if filter_tahun:
        bkd_list = bkd_list.filter(periode__tahun_akademik=filter_tahun)
    if filter_semester:
        bkd_list = bkd_list.filter(periode__semester_aktif=filter_semester)

    context = {
        'target_user': target_user,
        'tahun_list': tahun_list,
        'periode_list': TahunAkademikPublik.objects.using('simda').all(),
        'bisa_edit': bisa_edit,
        'input_terbuka': input_terbuka,
        'filter_tahun': filter_tahun,
        'filter_semester': filter_semester,
        'bkd_list': attach_dokumen_count(bkd_list, 'bkd'),
    }
    return render(request, 'kinerja/bkd.html', context)


@login_required
def tambah_bkd(request):
    if request.method != 'POST':
        return redirect('kinerja:bkd_index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('kinerja:bkd_index')

    user = request.user
    dosen_id = request.POST.get('dosen_id')
    target_user = get_object_or_404(User, id=dosen_id) if dosen_id and user.role in ['admin', 'operator'] else user
    dosen = get_simda_dosen_or_none(target_user)
    if not dosen:
        messages.error(request, 'NIDN Anda belum cocok dengan data di SIMDA. Hubungi admin.')
        return redirect('kinerja:bkd_index')

    periode_id = request.POST.get('periode_id')

    if RiwayatBKD.objects.filter(dosen=dosen, periode_id=periode_id).exists():
        messages.error(request, 'BKD untuk periode ini sudah ada.')
        return redirect('kinerja:bkd_index')

    bkd = RiwayatBKD(
        dosen=dosen,
        periode_id=periode_id,
        sks_pengajaran=request.POST.get('sks_pengajaran') or None,
        sks_penelitian=request.POST.get('sks_penelitian') or None,
        sks_pkm=request.POST.get('sks_pkm') or None,
        sks_penunjang=request.POST.get('sks_penunjang') or None,
        link_bkd=request.POST.get('link_bkd', '').strip(),
        keterangan=request.POST.get('keterangan', '').strip(),
    )
    if 'file_bkd' in request.FILES:
        bkd.file_bkd = request.FILES['file_bkd']
    bkd.save()
    messages.success(request, 'BKD berhasil disimpan ke SIMDA.')
    return redirect('kinerja:bkd_index')


@login_required
def hapus_bkd(request, bkd_id):
    bkd = get_object_or_404(RiwayatBKD, id=bkd_id)
    if request.user.nidn != bkd.dosen.nidn and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('kinerja:bkd_index')
    bkd.delete()
    messages.success(request, 'BKD berhasil dihapus.')
    return redirect('kinerja:bkd_index')


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
def tambah_penghargaan(request):
    if request.method != 'POST':
        return redirect('kinerja:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('kinerja:index')

    user = request.user
    dosen_id = request.POST.get('dosen_id')
    target_user = get_object_or_404(User, id=dosen_id) if dosen_id and user.role in ['admin', 'operator'] else user

    Penghargaan.objects.create(
        user=target_user,
        kode_prodi=target_user.kode_prodi or '',
        kode_fakultas=target_user.kode_fakultas or '',
        nama_penghargaan=request.POST.get('nama_penghargaan', '').strip(),
        lembaga_pemberi=request.POST.get('lembaga_pemberi', '').strip(),
        tingkat=request.POST.get('tingkat', ''),
        tahun=request.POST.get('tahun') or None,
        semester=request.POST.get('semester', ''),
        tahun_akademik=request.POST.get('tahun_akademik', ''),
        link_bukti=request.POST.get('link_bukti', '').strip(),
        updated_by=user.username
    )
    messages.success(request, 'Data penghargaan berhasil ditambahkan.')
    return redirect('kinerja:index')


@login_required
def hapus_penghargaan(request, id):
    obj = get_object_or_404(Penghargaan, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('kinerja:index')
    obj.delete()
    messages.success(request, 'Data penghargaan berhasil dihapus.')
    return redirect('kinerja:index')


@login_required
def edit_penghargaan(request, id):
    obj = get_object_or_404(Penghargaan, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('kinerja:index')
    if request.method == 'POST':
        obj.nama_penghargaan = request.POST.get('nama_penghargaan', '').strip()
        obj.lembaga_pemberi = request.POST.get('lembaga_pemberi', '').strip()
        obj.tingkat = request.POST.get('tingkat', obj.tingkat)
        obj.tahun = request.POST.get('tahun') or None
        obj.semester = request.POST.get('semester', '')
        obj.tahun_akademik = request.POST.get('tahun_akademik', obj.tahun_akademik)
        obj.link_bukti = request.POST.get('link_bukti', '').strip() or None
        obj.updated_by = request.user.username
        obj.save()
        messages.success(request, 'Data penghargaan berhasil diupdate.')
    return redirect('kinerja:index')


@login_required
def tambah_penunjang(request):
    if request.method != 'POST':
        return redirect('kinerja:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('kinerja:index')

    user = request.user
    dosen_id = request.POST.get('dosen_id')
    target_user = get_object_or_404(User, id=dosen_id) if dosen_id and user.role in ['admin', 'operator'] else user

    KegiatanPenunjang.objects.create(
        user=target_user,
        kode_prodi=target_user.kode_prodi or '',
        kode_fakultas=target_user.kode_fakultas or '',
        jenis_kegiatan=request.POST.get('jenis_kegiatan', ''),
        nama_kegiatan=request.POST.get('nama_kegiatan', '').strip(),
        peran=request.POST.get('peran', '').strip(),
        penyelenggara=request.POST.get('penyelenggara', '').strip(),
        tingkat=request.POST.get('tingkat', ''),
        tanggal_mulai=request.POST.get('tanggal_mulai') or None,
        tanggal_selesai=request.POST.get('tanggal_selesai') or None,
        semester=request.POST.get('semester', ''),
        tahun_akademik=request.POST.get('tahun_akademik', ''),
        link_bukti=request.POST.get('link_bukti', '').strip(),
        updated_by=user.username
    )
    messages.success(request, 'Kegiatan penunjang berhasil ditambahkan.')
    return redirect('kinerja:index')


@login_required
def hapus_penunjang(request, id):
    obj = get_object_or_404(KegiatanPenunjang, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('kinerja:index')
    obj.delete()
    messages.success(request, 'Kegiatan penunjang berhasil dihapus.')
    return redirect('kinerja:index')


@login_required
def edit_penunjang(request, id):
    obj = get_object_or_404(KegiatanPenunjang, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('kinerja:index')
    if request.method == 'POST':
        obj.jenis_kegiatan = request.POST.get('jenis_kegiatan', obj.jenis_kegiatan)
        obj.nama_kegiatan = request.POST.get('nama_kegiatan', '').strip()
        obj.peran = request.POST.get('peran', '').strip()
        obj.penyelenggara = request.POST.get('penyelenggara', '').strip()
        obj.tingkat = request.POST.get('tingkat', obj.tingkat)
        obj.tanggal_mulai = request.POST.get('tanggal_mulai') or None
        obj.tanggal_selesai = request.POST.get('tanggal_selesai') or None
        obj.semester = request.POST.get('semester', '')
        obj.tahun_akademik = request.POST.get('tahun_akademik', obj.tahun_akademik)
        obj.link_bukti = request.POST.get('link_bukti', '').strip() or None
        obj.updated_by = request.user.username
        obj.save()
        messages.success(request, 'Kegiatan penunjang berhasil diupdate.')
    return redirect('kinerja:index')


from django.core.exceptions import ValidationError
import os

def validate_dokumen(file):
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ['.pdf', '.jpg', '.jpeg', '.png']:
        raise ValidationError('Hanya PDF, JPG, PNG yang diizinkan.')
    if file.size > 5 * 1024 * 1024:
        raise ValidationError('Ukuran file maksimal 5MB.')


PENDIDIKAN_JENIS = {
    'pengajaran', 'bimbingan_mahasiswa', 'pengujian_mahasiswa', 'bahan_ajar',
    'pembinaan_mahasiswa', 'orasi_ilmiah', 'tugas_tambahan',
}
PENELITIAN_JENIS = {'penelitian', 'publikasi', 'hki'}


def _kembali_url(jenis_kinerja):
    if jenis_kinerja == 'bkd':
        return 'kinerja:bkd_index'
    if jenis_kinerja in PENDIDIKAN_JENIS:
        return 'pendidikan:index'
    if jenis_kinerja in PENELITIAN_JENIS:
        return 'penelitian:index'
    if jenis_kinerja == 'diklat':
        return 'profil:kualifikasi_index'
    if jenis_kinerja in ('sertifikasi', 'tes'):
        return 'profil:kompetensi_index'
    return 'kinerja:index'


@login_required
def kelola_dokumen(request, jenis_kinerja, kinerja_id):
    user = request.user

    # Validasi akses dan ambil objek kinerja
    KINERJA_MAP = {
        'penelitian': Penelitian,
        'publikasi': PublikasiKarya,
        'pkm': PKM,
        'hki': PatenHki,
        'bkd': RiwayatBKD,
        'pengajaran': Pengajaran,
        'bimbingan_mahasiswa': BimbinganMahasiswa,
        'pengujian_mahasiswa': PengujianMahasiswa,
        'bahan_ajar': BahanAjar,
        'pembinaan_mahasiswa': PembinaanMahasiswa,
        'orasi_ilmiah': OrasiIlmiah,
        'tugas_tambahan': TugasTambahan,
        'penghargaan': Penghargaan,
        'penunjang': KegiatanPenunjang,
        'diklat': Diklat,
        'sertifikasi': Sertifikasi,
        'tes': TesKompetensi,
    }

    if jenis_kinerja not in KINERJA_MAP:
        messages.error(request, 'Jenis kinerja tidak valid.')
        return redirect('kinerja:index')

    Model = KINERJA_MAP[jenis_kinerja]
    kinerja_obj = get_object_or_404(Model, id=kinerja_id)

    # BKD dimiliki DataDosen (SIMDA), bukan User (SIKD) -- resolve balik ke
    # User SIKD lewat nidn supaya DokumenKinerja (yang FK ke User) tetap konsisten.
    if jenis_kinerja == 'bkd':
        pemilik = User.objects.filter(nidn=kinerja_obj.dosen.nidn).first()
    else:
        pemilik = kinerja_obj.user

    # bisa_kelola = boleh tambah/edit/hapus dokumen (pemilik asli/admin saja).
    # Selain itu, dosen yang jadi Penulis/Anggota Dosen (co-author) di Bahan
    # Ajar/Penelitian/Publikasi Karya/Paten-HKI boleh LIHAT saja.
    bisa_kelola = (pemilik == user or user.role in ['admin', 'operator'])

    if not bisa_kelola:
        boleh_lihat = False
        if jenis_kinerja == 'bahan_ajar':
            dosen = get_simda_dosen_or_none(user)
            boleh_lihat = dosen and kinerja_obj.penulis_set.filter(
                jenis_penulis='dosen', dosen_id=dosen.id
            ).exists()
        elif jenis_kinerja == 'penelitian':
            dosen = get_simda_dosen_or_none(user)
            boleh_lihat = dosen and kinerja_obj.anggota_set.filter(
                jenis_anggota='dosen', dosen_id=dosen.id
            ).exists()
        elif jenis_kinerja in ('publikasi', 'hki'):
            dosen = get_simda_dosen_or_none(user)
            boleh_lihat = dosen and kinerja_obj.penulis_set.filter(
                jenis_penulis='dosen', dosen_id=dosen.id
            ).exists()
        if not boleh_lihat:
            messages.error(request, 'Anda tidak memiliki akses.')
            return redirect(_kembali_url(jenis_kinerja))

    dokumen_list = DokumenKinerja.objects.filter(
        user=pemilik,
        jenis_kinerja=jenis_kinerja,
        kinerja_id=kinerja_id
    ).order_by('jenis_dokumen')

    if request.method == 'POST':
        if not bisa_kelola:
            messages.error(request, 'Anda tidak memiliki akses untuk mengubah dokumen ini.')
            return redirect('kinerja:kelola_dokumen', jenis_kinerja=jenis_kinerja, kinerja_id=kinerja_id)

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
                    user=pemilik,
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
            if dok.user == pemilik or user.role in ['admin', 'operator']:
                nama = dok.nama_dokumen
                dok.delete()
                messages.success(request, f'Dokumen "{nama}" berhasil dihapus.')
        elif aksi == 'edit':
            dok_id = request.POST.get('dok_id')
            dok = get_object_or_404(DokumenKinerja, id=dok_id)
            if dok.user == pemilik or user.role in ['admin', 'operator']:
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
    elif hasattr(kinerja_obj, 'judul_kegiatan'):
        judul_kinerja = kinerja_obj.judul_kegiatan[:80]
    elif hasattr(kinerja_obj, 'judul_artikel'):
        judul_kinerja = kinerja_obj.judul_artikel[:80]
    elif hasattr(kinerja_obj, 'judul_karya'):
        judul_kinerja = kinerja_obj.judul_karya[:80]
    elif hasattr(kinerja_obj, 'nama_mk'):
        judul_kinerja = kinerja_obj.nama_mk[:80]
    elif hasattr(kinerja_obj, 'judul_bimbingan'):
        judul_kinerja = kinerja_obj.judul_bimbingan[:80]
    elif hasattr(kinerja_obj, 'judul_pengujian'):
        judul_kinerja = kinerja_obj.judul_pengujian[:80]
    elif hasattr(kinerja_obj, 'judul_orasi'):
        judul_kinerja = kinerja_obj.judul_orasi[:80]
    elif hasattr(kinerja_obj, 'jabatan_tambahan'):
        judul_kinerja = kinerja_obj.jabatan_tambahan[:80]
    elif hasattr(kinerja_obj, 'nama_kegiatan'):
        judul_kinerja = kinerja_obj.nama_kegiatan[:80]
    elif hasattr(kinerja_obj, 'nama_penghargaan'):
        judul_kinerja = kinerja_obj.nama_penghargaan[:80]
    elif hasattr(kinerja_obj, 'nama_diklat'):
        judul_kinerja = kinerja_obj.nama_diklat[:80]
    elif hasattr(kinerja_obj, 'nama_tes'):
        judul_kinerja = kinerja_obj.nama_tes[:80]
    elif hasattr(kinerja_obj, 'bidang_studi'):
        judul_kinerja = f'Sertifikasi {kinerja_obj.bidang_studi}'[:80]
    else:
        judul_kinerja = f'BKD periode {kinerja_obj.periode}'

    context = {
        'kinerja_obj': kinerja_obj,
        'pemilik': pemilik,
        'jenis_kinerja': jenis_kinerja,
        'kinerja_id': kinerja_id,
        'judul_kinerja': judul_kinerja,
        'dokumen_list': dokumen_list,
        'jenis_dokumen_choices': DokumenKinerja.JENIS_DOKUMEN,
        'kembali_url': _kembali_url(jenis_kinerja),
        'bisa_kelola': bisa_kelola,
    }
    return render(request, 'kinerja/kelola_dokumen.html', context)

@login_required
def edit_bkd(request, id):
    obj = get_object_or_404(RiwayatBKD, id=id)
    is_owner = request.user.nidn == obj.dosen.nidn
    is_admin = request.user.role in ['admin', 'operator']
    if not is_owner and not is_admin:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('kinerja:bkd_index')
    if request.method == 'POST':
        obj.sks_pengajaran = request.POST.get('sks_pengajaran') or None
        obj.sks_penelitian = request.POST.get('sks_penelitian') or None
        obj.sks_pkm = request.POST.get('sks_pkm') or None
        obj.sks_penunjang = request.POST.get('sks_penunjang') or None
        obj.link_bkd = request.POST.get('link_bkd', '').strip() or None
        obj.keterangan = request.POST.get('keterangan', '').strip()
        if 'file_bkd' in request.FILES:
            obj.file_bkd = request.FILES['file_bkd']
        # Hanya admin/kaprodi/sekprodi/dekan/wadek/rektorat yang boleh sahkan BKD --
        # dosen pemilik record tidak bisa mengesahkan BKD-nya sendiri.
        if request.user.role in RiwayatBKD.ROLE_BOLEH_SAHKAN:
            obj.status_pengesahan = request.POST.get('status_pengesahan', obj.status_pengesahan)
        obj.save()
        messages.success(request, 'BKD berhasil diupdate.')
    return redirect('kinerja:bkd_index')


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
