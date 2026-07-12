from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from master.models import TahunAkademik, Pengaturan
from accounts.models import User
from simda_dosen.models import MataKuliahPublik, MahasiswaPublik, ProdiPublik, DataDosen
from simda_dosen.utils import get_simda_dosen_or_none
from kinerja.utils import attach_dokumen_count
from .models import (
    Pengajaran, BimbinganMahasiswa, PengujianMahasiswa, BahanAjar,
    PenulisBahanAjar, PembinaanMahasiswa, OrasiIlmiah, TugasTambahan,
)

PER_PAGE_CHOICES = [10, 20, 50, 100]
DEFAULT_PER_PAGE = 20


def cek_status_input():
    try:
        p = Pengaturan.objects.first()
        return p.status_input == 'buka' if p else True
    except:
        return True


def _target_user(request, from_post=False):
    user = request.user
    source = request.POST if from_post else request.GET
    dosen_id = source.get('dosen_id')
    if dosen_id and user.role in ['admin', 'kaprodi', 'sekprodi', 'operator', 'dekan', 'wadek', 'rektorat', 'biro']:
        return get_object_or_404(User, id=dosen_id)
    return user


def _periode_choices(tahun_list):
    """Dropdown Periode gabungan Tahun Akademik + Semester (mis. "2025/2026
    Genap"), mengikuti tampilan filter Periode di SISTER BKD. Value-nya
    "{tahun_akademik}|{semester}" supaya gampang dipecah lagi saat filter."""
    choices = []
    for t in tahun_list:
        choices.append((f'{t.tahun_akademik}|Ganjil', f'{t.tahun_akademik} Ganjil'))
        choices.append((f'{t.tahun_akademik}|Genap', f'{t.tahun_akademik} Genap'))
    return choices


def _apply_periode(qs, periode_value):
    if not periode_value or '|' not in periode_value:
        return qs
    tahun, semester = periode_value.split('|', 1)
    # Record dengan semester='Keduanya' dianggap berlaku di kedua semester
    # tahun akademik itu, jadi tetap ikut match periode manapun yang dipilih.
    return qs.filter(tahun_akademik=tahun).filter(Q(semester=semester) | Q(semester='Keduanya'))


def _paginate(request, qs, page_param, per_page):
    paginator = Paginator(qs, per_page)
    return paginator.get_page(request.GET.get(page_param, 1))


def _attach_dokumen_count(page_obj, jenis_kinerja):
    """Nempelin .jumlah_dokumen ke objek di halaman ini saja (bukan seluruh
    data) supaya query tetap ringan biar berapa pun banyaknya data lama."""
    attach_dokumen_count(page_obj.object_list, jenis_kinerja)
    return page_obj


def _bahan_ajar_queryset(target_user):
    """Bahan Ajar milik target_user sendiri, ditambah Bahan Ajar milik dosen
    lain yang mencantumkan target_user sebagai Penulis Dosen (co-author) --
    supaya karya bersama ikut terhitung kinerja semua dosen penulisnya.
    Mahasiswa co-author sengaja tidak diberi perlakuan sama (tidak punya
    akun kinerja di SIKD)."""
    qs = BahanAjar.objects.filter(user=target_user)
    dosen = get_simda_dosen_or_none(target_user)
    if dosen:
        qs = qs | BahanAjar.objects.filter(
            penulis_set__jenis_penulis='dosen', penulis_set__dosen_id=dosen.id
        )
    return qs.select_related('user').distinct()


def _attach_bahan_ajar_extras(page_obj, target_user):
    """Tandai baris yang muncul karena co-authorship (bukan input sendiri)
    supaya template bisa kasih badge & sembunyikan tombol Edit/Hapus --
    hanya pemilik asli yang boleh ubah/hapus data intinya."""
    for o in page_obj.object_list:
        o.co_penulis = (o.user_id != target_user.id)
    return page_obj


@login_required
def index(request):
    user = request.user
    target_user = _target_user(request)

    tahun_list = TahunAkademik.objects.filter(status='aktif').order_by('-urutan')
    input_terbuka = cek_status_input()
    bisa_edit = (user == target_user or user.role in ['admin', 'operator']) and input_terbuka

    try:
        per_page = int(request.GET.get('per_page', DEFAULT_PER_PAGE))
    except (TypeError, ValueError):
        per_page = DEFAULT_PER_PAGE
    if per_page not in PER_PAGE_CHOICES:
        per_page = DEFAULT_PER_PAGE

    periode_choices = _periode_choices(tahun_list)
    periode_peng = request.GET.get('periode_peng', '')
    periode_bim = request.GET.get('periode_bim', '')
    periode_uji = request.GET.get('periode_uji', '')
    periode_pm = request.GET.get('periode_pm', '')

    pengajaran_qs = _apply_periode(target_user.pengajaran_set.all(), periode_peng)
    bimbingan_qs = _apply_periode(target_user.bimbingan_set.all(), periode_bim)
    pengujian_qs = _apply_periode(target_user.pengujian_set.all(), periode_uji)
    pembinaan_qs = _apply_periode(target_user.pembinaan_mahasiswa_set.all(), periode_pm)

    context = {
        'target_user': target_user,
        'tahun_list': tahun_list,
        'bisa_edit': bisa_edit,
        'input_terbuka': input_terbuka,
        'prodi_list': ProdiPublik.objects.using('simda').all(),
        'per_page': per_page,
        'per_page_choices': PER_PAGE_CHOICES,
        'periode_choices': periode_choices,
        'periode_peng': periode_peng,
        'periode_bim': periode_bim,
        'periode_uji': periode_uji,
        'periode_pm': periode_pm,
        'pengajaran_list': _attach_dokumen_count(_paginate(request, pengajaran_qs, 'page_peng', per_page), 'pengajaran'),
        'bimbingan_list': _attach_dokumen_count(_paginate(request, bimbingan_qs, 'page_bim', per_page), 'bimbingan_mahasiswa'),
        'pengujian_list': _attach_dokumen_count(_paginate(request, pengujian_qs, 'page_uji', per_page), 'pengujian_mahasiswa'),
        'bahan_ajar_list': _attach_dokumen_count(
            _attach_bahan_ajar_extras(_paginate(request, _bahan_ajar_queryset(target_user), 'page_ba', per_page), target_user),
            'bahan_ajar'
        ),
        'pembinaan_mahasiswa_list': _attach_dokumen_count(_paginate(request, pembinaan_qs, 'page_pm', per_page), 'pembinaan_mahasiswa'),
        'orasi_ilmiah_list': _attach_dokumen_count(_paginate(request, target_user.orasi_ilmiah_set.all(), 'page_oi', per_page), 'orasi_ilmiah'),
        'tugas_tambahan_list': _attach_dokumen_count(_paginate(request, target_user.tugas_tambahan_set.all(), 'page_tt', per_page), 'tugas_tambahan'),
    }
    return render(request, 'pendidikan/index.html', context)


# ============================================================
# PENGAJARAN
# ============================================================

@login_required
def tambah_pengajaran(request):
    if request.method != 'POST':
        return redirect('pendidikan:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('pendidikan:index')

    target_user = _target_user(request, from_post=True)
    mk_id = request.POST.get('mata_kuliah_id')
    mk = get_object_or_404(MataKuliahPublik.objects.using('simda'), id=mk_id) if mk_id else None
    if not mk:
        messages.error(request, 'Mata kuliah wajib dipilih.')
        return redirect('pendidikan:index')

    Pengajaran.objects.create(
        user=target_user,
        kode_prodi=target_user.kode_prodi or '',
        kode_fakultas=target_user.kode_fakultas or '',
        prodi_mengajar_kode=request.POST.get('prodi_mengajar_kode', '').strip(),
        no_sk_penugasan=request.POST.get('no_sk_penugasan', '').strip(),
        tanggal_sk_penugasan=request.POST.get('tanggal_sk_penugasan') or None,
        mata_kuliah_id=mk.id,
        kode_mk=mk.kode_mk,
        nama_mk=mk.nama_mk,
        jenis_mk=mk.jenis_mk,
        sks_total=mk.sks_total,
        nama_kelas=request.POST.get('nama_kelas', '').strip(),
        jumlah_pertemuan=request.POST.get('jumlah_pertemuan') or None,
        jumlah_mahasiswa=request.POST.get('jumlah_mahasiswa', 0) or 0,
        semester=request.POST.get('semester', ''),
        tahun_akademik=request.POST.get('tahun_akademik', ''),
        updated_by=request.user.username,
    )
    messages.success(request, 'Data pengajaran berhasil ditambahkan.')
    return redirect('pendidikan:index')


@login_required
def edit_pengajaran(request, id):
    obj = get_object_or_404(Pengajaran, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('pendidikan:index')
    if request.method == 'POST':
        mk_id = request.POST.get('mata_kuliah_id')
        if mk_id:
            mk = get_object_or_404(MataKuliahPublik.objects.using('simda'), id=mk_id)
            obj.mata_kuliah_id = mk.id
            obj.kode_mk = mk.kode_mk
            obj.nama_mk = mk.nama_mk
            obj.jenis_mk = mk.jenis_mk
            obj.sks_total = mk.sks_total
        obj.prodi_mengajar_kode = request.POST.get('prodi_mengajar_kode', '').strip()
        obj.no_sk_penugasan = request.POST.get('no_sk_penugasan', '').strip()
        obj.tanggal_sk_penugasan = request.POST.get('tanggal_sk_penugasan') or None
        obj.nama_kelas = request.POST.get('nama_kelas', '').strip()
        obj.jumlah_pertemuan = request.POST.get('jumlah_pertemuan') or None
        obj.jumlah_mahasiswa = request.POST.get('jumlah_mahasiswa', 0) or 0
        obj.semester = request.POST.get('semester', '')
        obj.tahun_akademik = request.POST.get('tahun_akademik', obj.tahun_akademik)
        obj.updated_by = request.user.username
        obj.save()
        messages.success(request, 'Data pengajaran berhasil diupdate.')
    return redirect('pendidikan:index')


@login_required
def hapus_pengajaran(request, id):
    obj = get_object_or_404(Pengajaran, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('pendidikan:index')
    obj.delete()
    messages.success(request, 'Data pengajaran berhasil dihapus.')
    return redirect('pendidikan:index')


# ============================================================
# BIMBINGAN MAHASISWA
# ============================================================

@login_required
def tambah_bimbingan(request):
    if request.method != 'POST':
        return redirect('pendidikan:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('pendidikan:index')

    target_user = _target_user(request, from_post=True)
    mhs_id = request.POST.get('mahasiswa_id')
    mhs = get_object_or_404(MahasiswaPublik.objects.using('simda'), id=mhs_id) if mhs_id else None
    if not mhs:
        messages.error(request, 'Mahasiswa wajib dipilih.')
        return redirect('pendidikan:index')

    BimbinganMahasiswa.objects.create(
        user=target_user,
        kode_prodi=target_user.kode_prodi or '',
        kode_fakultas=target_user.kode_fakultas or '',
        prodi_mahasiswa_kode=request.POST.get('prodi_mahasiswa_kode', '').strip(),
        jenis_bimbingan=request.POST.get('jenis_bimbingan', ''),
        no_sk_penugasan=request.POST.get('no_sk_penugasan', '').strip(),
        tanggal_sk_penugasan=request.POST.get('tanggal_sk_penugasan') or None,
        mahasiswa_id=mhs.id,
        nim=mhs.nim,
        nama_mahasiswa=mhs.nama_lengkap,
        judul_bimbingan=request.POST.get('judul_bimbingan', '').strip(),
        kategori=request.POST.get('kategori', ''),
        semester=request.POST.get('semester', ''),
        tahun_akademik=request.POST.get('tahun_akademik', ''),
        updated_by=request.user.username,
    )
    messages.success(request, 'Data bimbingan mahasiswa berhasil ditambahkan.')
    return redirect('pendidikan:index')


@login_required
def edit_bimbingan(request, id):
    obj = get_object_or_404(BimbinganMahasiswa, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('pendidikan:index')
    if request.method == 'POST':
        mhs_id = request.POST.get('mahasiswa_id')
        if mhs_id:
            mhs = get_object_or_404(MahasiswaPublik.objects.using('simda'), id=mhs_id)
            obj.mahasiswa_id = mhs.id
            obj.nim = mhs.nim
            obj.nama_mahasiswa = mhs.nama_lengkap
        obj.prodi_mahasiswa_kode = request.POST.get('prodi_mahasiswa_kode', '').strip()
        obj.jenis_bimbingan = request.POST.get('jenis_bimbingan', obj.jenis_bimbingan)
        obj.no_sk_penugasan = request.POST.get('no_sk_penugasan', '').strip()
        obj.tanggal_sk_penugasan = request.POST.get('tanggal_sk_penugasan') or None
        obj.judul_bimbingan = request.POST.get('judul_bimbingan', '').strip()
        obj.kategori = request.POST.get('kategori', obj.kategori)
        obj.semester = request.POST.get('semester', '')
        obj.tahun_akademik = request.POST.get('tahun_akademik', obj.tahun_akademik)
        obj.updated_by = request.user.username
        obj.save()
        messages.success(request, 'Data bimbingan mahasiswa berhasil diupdate.')
    return redirect('pendidikan:index')


@login_required
def hapus_bimbingan(request, id):
    obj = get_object_or_404(BimbinganMahasiswa, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('pendidikan:index')
    obj.delete()
    messages.success(request, 'Data bimbingan mahasiswa berhasil dihapus.')
    return redirect('pendidikan:index')


# ============================================================
# PENGUJIAN MAHASISWA
# ============================================================

@login_required
def tambah_pengujian(request):
    if request.method != 'POST':
        return redirect('pendidikan:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('pendidikan:index')

    target_user = _target_user(request, from_post=True)
    mhs_id = request.POST.get('mahasiswa_id')
    mhs = get_object_or_404(MahasiswaPublik.objects.using('simda'), id=mhs_id) if mhs_id else None
    if not mhs:
        messages.error(request, 'Mahasiswa wajib dipilih.')
        return redirect('pendidikan:index')

    PengujianMahasiswa.objects.create(
        user=target_user,
        kode_prodi=target_user.kode_prodi or '',
        kode_fakultas=target_user.kode_fakultas or '',
        prodi_mahasiswa_kode=request.POST.get('prodi_mahasiswa_kode', '').strip(),
        no_sk_penugasan=request.POST.get('no_sk_penugasan', '').strip(),
        tanggal_sk_penugasan=request.POST.get('tanggal_sk_penugasan') or None,
        mahasiswa_id=mhs.id,
        nim=mhs.nim,
        nama_mahasiswa=mhs.nama_lengkap,
        judul_pengujian=request.POST.get('judul_pengujian', '').strip(),
        kategori=request.POST.get('kategori', ''),
        semester=request.POST.get('semester', ''),
        tahun_akademik=request.POST.get('tahun_akademik', ''),
        updated_by=request.user.username,
    )
    messages.success(request, 'Data pengujian mahasiswa berhasil ditambahkan.')
    return redirect('pendidikan:index')


@login_required
def edit_pengujian(request, id):
    obj = get_object_or_404(PengujianMahasiswa, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('pendidikan:index')
    if request.method == 'POST':
        mhs_id = request.POST.get('mahasiswa_id')
        if mhs_id:
            mhs = get_object_or_404(MahasiswaPublik.objects.using('simda'), id=mhs_id)
            obj.mahasiswa_id = mhs.id
            obj.nim = mhs.nim
            obj.nama_mahasiswa = mhs.nama_lengkap
        obj.prodi_mahasiswa_kode = request.POST.get('prodi_mahasiswa_kode', '').strip()
        obj.no_sk_penugasan = request.POST.get('no_sk_penugasan', '').strip()
        obj.tanggal_sk_penugasan = request.POST.get('tanggal_sk_penugasan') or None
        obj.judul_pengujian = request.POST.get('judul_pengujian', '').strip()
        obj.kategori = request.POST.get('kategori', obj.kategori)
        obj.semester = request.POST.get('semester', '')
        obj.tahun_akademik = request.POST.get('tahun_akademik', obj.tahun_akademik)
        obj.updated_by = request.user.username
        obj.save()
        messages.success(request, 'Data pengujian mahasiswa berhasil diupdate.')
    return redirect('pendidikan:index')


@login_required
def hapus_pengujian(request, id):
    obj = get_object_or_404(PengujianMahasiswa, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('pendidikan:index')
    obj.delete()
    messages.success(request, 'Data pengujian mahasiswa berhasil dihapus.')
    return redirect('pendidikan:index')


# ============================================================
# BAHAN AJAR
# ============================================================

@login_required
def tambah_bahan_ajar(request):
    if request.method != 'POST':
        return redirect('pendidikan:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('pendidikan:index')

    target_user = _target_user(request, from_post=True)
    BahanAjar.objects.create(
        user=target_user,
        kode_prodi=target_user.kode_prodi or '',
        kode_fakultas=target_user.kode_fakultas or '',
        jenis_bahan_ajar=request.POST.get('jenis_bahan_ajar', ''),
        judul=request.POST.get('judul', '').strip(),
        isbn=request.POST.get('isbn', '').strip(),
        penerbit=request.POST.get('penerbit', '').strip(),
        tahun_terbit=request.POST.get('tahun_terbit') or None,
        jumlah_halaman=request.POST.get('jumlah_halaman') or None,
        semester=request.POST.get('semester', ''),
        tahun_akademik=request.POST.get('tahun_akademik', ''),
        updated_by=request.user.username,
    )
    messages.success(request, 'Data bahan ajar berhasil ditambahkan.')
    return redirect('pendidikan:index')


@login_required
def edit_bahan_ajar(request, id):
    obj = get_object_or_404(BahanAjar, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('pendidikan:index')
    if request.method == 'POST':
        obj.jenis_bahan_ajar = request.POST.get('jenis_bahan_ajar', obj.jenis_bahan_ajar)
        obj.judul = request.POST.get('judul', '').strip()
        obj.isbn = request.POST.get('isbn', '').strip()
        obj.penerbit = request.POST.get('penerbit', '').strip()
        obj.tahun_terbit = request.POST.get('tahun_terbit') or obj.tahun_terbit
        obj.jumlah_halaman = request.POST.get('jumlah_halaman') or None
        obj.semester = request.POST.get('semester', '')
        obj.tahun_akademik = request.POST.get('tahun_akademik', '')
        obj.updated_by = request.user.username
        obj.save()
        messages.success(request, 'Data bahan ajar berhasil diupdate.')
    return redirect('pendidikan:index')


@login_required
def hapus_bahan_ajar(request, id):
    obj = get_object_or_404(BahanAjar, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('pendidikan:index')
    obj.delete()
    messages.success(request, 'Data bahan ajar berhasil dihapus.')
    return redirect('pendidikan:index')


# ============================================================
# PENULIS BAHAN AJAR (satu Bahan Ajar bisa punya banyak penulis)
# ============================================================

@login_required
def kelola_penulis(request, bahan_ajar_id):
    bahan_ajar = get_object_or_404(BahanAjar, id=bahan_ajar_id)
    user = request.user
    bisa_edit = (user == bahan_ajar.user or user.role in ['admin', 'operator']) and cek_status_input()

    # Selain pemilik asli/admin, dosen yang jadi Penulis Dosen (co-author)
    # di record ini boleh LIHAT saja (bisa_edit tetap False untuk mereka).
    if bahan_ajar.user != user and user.role not in ['admin', 'operator']:
        dosen = get_simda_dosen_or_none(user)
        is_co_penulis = dosen and bahan_ajar.penulis_set.filter(
            jenis_penulis='dosen', dosen_id=dosen.id
        ).exists()
        if not is_co_penulis:
            messages.error(request, 'Tidak memiliki akses.')
            return redirect('pendidikan:index')

    if request.method == 'POST':
        aksi = request.POST.get('aksi')

        if aksi == 'tambah':
            if not bisa_edit:
                messages.error(request, 'Input data sedang dikunci.')
                return redirect('pendidikan:kelola_penulis', bahan_ajar_id=bahan_ajar_id)

            jenis_penulis = request.POST.get('jenis_penulis', '')
            penulis = PenulisBahanAjar(
                bahan_ajar=bahan_ajar,
                jenis_penulis=jenis_penulis,
                urutan=request.POST.get('urutan') or 1,
                afiliasi=request.POST.get('afiliasi', '').strip(),
                peran=request.POST.get('peran', 'penulis'),
                updated_by=user.username,
            )
            if jenis_penulis == 'dosen':
                dosen_id = request.POST.get('dosen_id')
                dosen = get_object_or_404(DataDosen.objects.using('simda'), id=dosen_id) if dosen_id else None
                if not dosen:
                    messages.error(request, 'Nama dosen wajib dipilih.')
                    return redirect('pendidikan:kelola_penulis', bahan_ajar_id=bahan_ajar_id)
                penulis.dosen_id = dosen.id
                penulis.nama = dosen.nama_lengkap_gelar
                penulis.nidn_nim = dosen.nidn
                penulis.afiliasi = penulis.afiliasi or 'Universitas Ichsan Gorontalo'
            elif jenis_penulis == 'mahasiswa':
                mhs_id = request.POST.get('mahasiswa_id')
                mhs = get_object_or_404(MahasiswaPublik.objects.using('simda'), id=mhs_id) if mhs_id else None
                if not mhs:
                    messages.error(request, 'Nama mahasiswa wajib dipilih.')
                    return redirect('pendidikan:kelola_penulis', bahan_ajar_id=bahan_ajar_id)
                penulis.mahasiswa_id = mhs.id
                penulis.nama = mhs.nama_lengkap
                penulis.nidn_nim = mhs.nim
                penulis.afiliasi = penulis.afiliasi or 'Universitas Ichsan Gorontalo'
            else:
                nama = request.POST.get('nama', '').strip()
                if not nama:
                    messages.error(request, 'Nama penulis wajib diisi.')
                    return redirect('pendidikan:kelola_penulis', bahan_ajar_id=bahan_ajar_id)
                penulis.nama = nama

            penulis.save()
            messages.success(request, f'Penulis "{penulis.nama}" berhasil ditambahkan.')

        elif aksi == 'edit':
            if not bisa_edit:
                messages.error(request, 'Input data sedang dikunci.')
                return redirect('pendidikan:kelola_penulis', bahan_ajar_id=bahan_ajar_id)
            penulis = get_object_or_404(PenulisBahanAjar, id=request.POST.get('penulis_id'), bahan_ajar=bahan_ajar)
            penulis.urutan = request.POST.get('urutan') or penulis.urutan
            penulis.afiliasi = request.POST.get('afiliasi', '').strip()
            penulis.peran = request.POST.get('peran', penulis.peran)
            if penulis.jenis_penulis == 'lain':
                penulis.nama = request.POST.get('nama', '').strip() or penulis.nama
            penulis.updated_by = user.username
            penulis.save()
            messages.success(request, 'Data penulis berhasil diupdate.')

        elif aksi == 'hapus':
            penulis = get_object_or_404(PenulisBahanAjar, id=request.POST.get('penulis_id'), bahan_ajar=bahan_ajar)
            if bisa_edit:
                nama = penulis.nama
                penulis.delete()
                messages.success(request, f'Penulis "{nama}" berhasil dihapus.')
            else:
                messages.error(request, 'Tidak memiliki akses.')

        return redirect('pendidikan:kelola_penulis', bahan_ajar_id=bahan_ajar_id)

    context = {
        'bahan_ajar': bahan_ajar,
        'bisa_edit': bisa_edit,
        'penulis_list': bahan_ajar.penulis_set.all(),
    }
    return render(request, 'pendidikan/kelola_penulis.html', context)


# ============================================================
# PEMBINAAN MAHASISWA
# ============================================================

@login_required
def tambah_pembinaan_mahasiswa(request):
    if request.method != 'POST':
        return redirect('pendidikan:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('pendidikan:index')

    target_user = _target_user(request, from_post=True)
    PembinaanMahasiswa.objects.create(
        user=target_user,
        kode_prodi=target_user.kode_prodi or '',
        kode_fakultas=target_user.kode_fakultas or '',
        jenis_kegiatan=request.POST.get('jenis_kegiatan', ''),
        nama_kegiatan=request.POST.get('nama_kegiatan', '').strip(),
        tingkat=request.POST.get('tingkat', ''),
        tahun=request.POST.get('tahun') or None,
        semester=request.POST.get('semester', ''),
        tahun_akademik=request.POST.get('tahun_akademik', ''),
        updated_by=request.user.username,
    )
    messages.success(request, 'Data pembinaan mahasiswa berhasil ditambahkan.')
    return redirect('pendidikan:index')


@login_required
def edit_pembinaan_mahasiswa(request, id):
    obj = get_object_or_404(PembinaanMahasiswa, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('pendidikan:index')
    if request.method == 'POST':
        obj.jenis_kegiatan = request.POST.get('jenis_kegiatan', obj.jenis_kegiatan)
        obj.nama_kegiatan = request.POST.get('nama_kegiatan', '').strip()
        obj.tingkat = request.POST.get('tingkat', obj.tingkat)
        obj.tahun = request.POST.get('tahun') or obj.tahun
        obj.semester = request.POST.get('semester', '')
        obj.tahun_akademik = request.POST.get('tahun_akademik', '')
        obj.updated_by = request.user.username
        obj.save()
        messages.success(request, 'Data pembinaan mahasiswa berhasil diupdate.')
    return redirect('pendidikan:index')


@login_required
def hapus_pembinaan_mahasiswa(request, id):
    obj = get_object_or_404(PembinaanMahasiswa, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('pendidikan:index')
    obj.delete()
    messages.success(request, 'Data pembinaan mahasiswa berhasil dihapus.')
    return redirect('pendidikan:index')


# ============================================================
# ORASI ILMIAH
# ============================================================

@login_required
def tambah_orasi_ilmiah(request):
    if request.method != 'POST':
        return redirect('pendidikan:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('pendidikan:index')

    target_user = _target_user(request, from_post=True)
    OrasiIlmiah.objects.create(
        user=target_user,
        kode_prodi=target_user.kode_prodi or '',
        kode_fakultas=target_user.kode_fakultas or '',
        judul_orasi=request.POST.get('judul_orasi', '').strip(),
        penyelenggara=request.POST.get('penyelenggara', '').strip(),
        tanggal=request.POST.get('tanggal') or None,
        tingkat=request.POST.get('tingkat', ''),
        semester=request.POST.get('semester', ''),
        tahun_akademik=request.POST.get('tahun_akademik', ''),
        updated_by=request.user.username,
    )
    messages.success(request, 'Data orasi ilmiah berhasil ditambahkan.')
    return redirect('pendidikan:index')


@login_required
def edit_orasi_ilmiah(request, id):
    obj = get_object_or_404(OrasiIlmiah, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('pendidikan:index')
    if request.method == 'POST':
        obj.judul_orasi = request.POST.get('judul_orasi', '').strip()
        obj.penyelenggara = request.POST.get('penyelenggara', '').strip()
        obj.tanggal = request.POST.get('tanggal') or obj.tanggal
        obj.tingkat = request.POST.get('tingkat', obj.tingkat)
        obj.semester = request.POST.get('semester', '')
        obj.tahun_akademik = request.POST.get('tahun_akademik', '')
        obj.updated_by = request.user.username
        obj.save()
        messages.success(request, 'Data orasi ilmiah berhasil diupdate.')
    return redirect('pendidikan:index')


@login_required
def hapus_orasi_ilmiah(request, id):
    obj = get_object_or_404(OrasiIlmiah, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('pendidikan:index')
    obj.delete()
    messages.success(request, 'Data orasi ilmiah berhasil dihapus.')
    return redirect('pendidikan:index')


# ============================================================
# TUGAS TAMBAHAN
# ============================================================

@login_required
def tambah_tugas_tambahan(request):
    if request.method != 'POST':
        return redirect('pendidikan:index')
    if not cek_status_input():
        messages.error(request, 'Input data sedang dikunci.')
        return redirect('pendidikan:index')

    target_user = _target_user(request, from_post=True)
    TugasTambahan.objects.create(
        user=target_user,
        kode_prodi=target_user.kode_prodi or '',
        kode_fakultas=target_user.kode_fakultas or '',
        jabatan_tambahan=request.POST.get('jabatan_tambahan', '').strip(),
        no_sk=request.POST.get('no_sk', '').strip(),
        tanggal_sk=request.POST.get('tanggal_sk') or None,
        tanggal_mulai=request.POST.get('tanggal_mulai') or None,
        tanggal_selesai=request.POST.get('tanggal_selesai') or None,
        semester=request.POST.get('semester', ''),
        tahun_akademik=request.POST.get('tahun_akademik', ''),
        updated_by=request.user.username,
    )
    messages.success(request, 'Data tugas tambahan berhasil ditambahkan.')
    return redirect('pendidikan:index')


@login_required
def edit_tugas_tambahan(request, id):
    obj = get_object_or_404(TugasTambahan, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('pendidikan:index')
    if request.method == 'POST':
        obj.jabatan_tambahan = request.POST.get('jabatan_tambahan', '').strip()
        obj.no_sk = request.POST.get('no_sk', '').strip()
        obj.tanggal_sk = request.POST.get('tanggal_sk') or None
        obj.tanggal_mulai = request.POST.get('tanggal_mulai') or obj.tanggal_mulai
        obj.tanggal_selesai = request.POST.get('tanggal_selesai') or None
        obj.semester = request.POST.get('semester', '')
        obj.tahun_akademik = request.POST.get('tahun_akademik', '')
        obj.updated_by = request.user.username
        obj.save()
        messages.success(request, 'Data tugas tambahan berhasil diupdate.')
    return redirect('pendidikan:index')


@login_required
def hapus_tugas_tambahan(request, id):
    obj = get_object_or_404(TugasTambahan, id=id)
    if request.user != obj.user and request.user.role not in ['admin', 'operator']:
        messages.error(request, 'Tidak memiliki akses.')
        return redirect('pendidikan:index')
    obj.delete()
    messages.success(request, 'Data tugas tambahan berhasil dihapus.')
    return redirect('pendidikan:index')
