from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    DataTendikForm, RiwayatPendidikanTendikForm, RiwayatPelatihanTendikForm, RiwayatPrestasiTendikForm,
)
from .models import (
    DataDosen, DataTendik, MahasiswaPublik, MataKuliahPublik,
    RiwayatPendidikanTendik, RiwayatPelatihanTendik, RiwayatPrestasiTendik,
)
from .utils import get_or_create_unit_kerja, get_simda_tendik_or_none


@login_required
def cari_mata_kuliah(request):
    """Dropdown+cari Mata Kuliah untuk form Pengajaran, difilter per prodi
    yang dipilih dosen (bisa lintas prodi, khususnya dosen MKDU)."""
    kode_prodi = request.GET.get('kode_prodi', '').strip()
    q = request.GET.get('q', '').strip()

    if not kode_prodi:
        return JsonResponse({'results': []})

    qs = MataKuliahPublik.objects.using('simda').filter(
        kode_prodi=kode_prodi, status=True
    )
    if q:
        qs = qs.filter(Q(kode_mk__icontains=q) | Q(nama_mk__icontains=q))

    results = [
        {
            'id': mk.id,
            'kode_mk': mk.kode_mk,
            'nama_mk': mk.nama_mk,
            'jenis_mk': mk.jenis_mk,
            'sks_total': mk.sks_total,
            'text': f'{mk.kode_mk} — {mk.nama_mk} ({mk.sks_total} SKS)',
        }
        for mk in qs.order_by('kode_mk')[:30]
    ]
    return JsonResponse({'results': results})


@login_required
def cari_mahasiswa(request):
    """Dropdown+cari Nama Mahasiswa untuk form Bimbingan & Pengujian Mahasiswa
    (difilter per prodi) dan Penulis Bahan Ajar (kode_prodi kosong = cari
    lintas semua prodi, karena co-author mahasiswa bisa dari prodi manapun).
    Minimal 3 huruf sebelum pencarian jalan (sesuai spek SISTER)."""
    kode_prodi = request.GET.get('kode_prodi', '').strip()
    q = request.GET.get('q', '').strip()

    if len(q) < 3:
        return JsonResponse({'results': []})

    qs = MahasiswaPublik.objects.using('simda').filter(status_mahasiswa='aktif')
    if kode_prodi:
        qs = qs.filter(kode_prodi=kode_prodi)
    qs = qs.filter(Q(nama_lengkap__icontains=q) | Q(nim__icontains=q))

    results = [
        {
            'id': m.id,
            'nim': m.nim,
            'nama_lengkap': m.nama_lengkap,
            'angkatan': m.angkatan,
            'text': f'{m.nim} — {m.nama_lengkap}',
        }
        for m in qs.order_by('nama_lengkap')[:30]
    ]
    return JsonResponse({'results': results})


@login_required
def cari_dosen(request):
    """Dropdown+cari Nama Dosen (internal Unisan) untuk form Penulis Bahan
    Ajar. Minimal 3 huruf, tidak difilter prodi (dosen bisa jadi co-author
    lintas prodi/fakultas)."""
    q = request.GET.get('q', '').strip()

    if len(q) < 3:
        return JsonResponse({'results': []})

    qs = DataDosen.objects.using('simda').filter(
        is_active=True
    ).filter(Q(nama_lengkap__icontains=q) | Q(nidn__icontains=q))

    results = [
        {
            'id': d.id,
            'nidn': d.nidn,
            'nama_lengkap': d.nama_lengkap_gelar,
            'text': f'{d.nidn} — {d.nama_lengkap_gelar}',
        }
        for d in qs.order_by('nama_lengkap')[:30]
    ]
    return JsonResponse({'results': results})


# ============================================================
# Kelola Data Tendik -- CRUD penuh ke master.data_tendik SIMDA,
# admin-only (BUKAN discope dapat_kelola seperti Kelola User -- data
# tendik tidak punya konsep fakultas/prodi untuk dipetakan ke situ,
# dan field-nya termasuk data pribadi sensitif/HR terpusat). Pembuatan
# akun LOGIN (accounts.User) TETAP langkah terpisah lewat Kelola User,
# lihat DataTendik.__doc__ untuk alasan lengkap.
# ============================================================

def _bisa_kelola_data_tendik(user):
    return user.role == 'admin'


def _bisa_kelola_riwayat_tendik(user, tendik):
    """Riwayat Pendidikan/Pelatihan/Prestasi Tendik boleh dikelola admin
    (siapa pun, lewat Kelola Data Tendik) ATAU tendik yang bersangkutan
    sendiri (self-service per 2026-08-04, dicocokkan lewat nip_yayasan --
    lihat get_simda_tendik_or_none) -- TIDAK tendik lain. Biodata TETAP
    admin-only (keputusan user) -- ini cuma untuk 3 riwayat."""
    if user.role == 'admin':
        return True
    if user.role == 'tendik':
        milik_sendiri = get_simda_tendik_or_none(user)
        return bool(milik_sendiri) and milik_sendiri.id == tendik.id
    return False


def _role_bisa_riwayat_tendik(role):
    """Pre-check MURNI role (tanpa fetch DataTendik/query 'simda') --
    dipanggil di awal tiap view riwayat SEBELUM get_object_or_404,
    supaya role yang jelas tidak berhak (mis. dosen/kaprodi) langsung
    ditolak tanpa perlu query ke database SIMDA sama sekali."""
    return role in ('admin', 'tendik')


def _redirect_setelah_riwayat_tendik(request, tendik_id):
    """Admin kembali ke halaman Profil Tendik (Kelola Data Tendik),
    tendik self-service kembali ke halaman Riwayat Saya sendiri."""
    if request.user.role == 'admin':
        return redirect('simda_dosen:detail_tendik', tendik_id=tendik_id)
    return redirect('simda_dosen:profil_riwayat_saya')


@login_required
def daftar_tendik(request):
    if not _bisa_kelola_data_tendik(request.user):
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")

    q = request.GET.get('q', '').strip()
    daftar = DataTendik.objects.using('simda').all()
    if q:
        daftar = daftar.filter(Q(nama_lengkap__icontains=q) | Q(nip__icontains=q) | Q(nip_yayasan__icontains=q))
    daftar = daftar.order_by('nama_lengkap')

    return render(request, 'simda_dosen/daftar_tendik.html', {'daftar': daftar, 'kata_kunci': q})


@login_required
def tambah_tendik(request):
    if not _bisa_kelola_data_tendik(request.user):
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")

    if request.method == 'POST':
        form = DataTendikForm(request.POST, request.FILES)
        if form.is_valid():
            unit_kerja_baru = form.cleaned_data.get('unit_kerja_baru', '').strip()
            if unit_kerja_baru:
                form.instance.unit_kerja_id = get_or_create_unit_kerja(unit_kerja_baru)
            form.save()
            messages.success(request, 'Data tendik berhasil ditambahkan.')
            return redirect('simda_dosen:daftar_tendik')
    else:
        form = DataTendikForm()
    return render(request, 'simda_dosen/tendik_form.html', {'form': form, 'judul': 'Tambah Data Tendik'})


@login_required
def ubah_tendik(request, tendik_id):
    if not _bisa_kelola_data_tendik(request.user):
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")

    tendik = get_object_or_404(DataTendik.objects.using('simda'), id=tendik_id)
    if request.method == 'POST':
        form = DataTendikForm(request.POST, request.FILES, instance=tendik)
        if form.is_valid():
            unit_kerja_baru = form.cleaned_data.get('unit_kerja_baru', '').strip()
            if unit_kerja_baru:
                form.instance.unit_kerja_id = get_or_create_unit_kerja(unit_kerja_baru)
            form.save()
            messages.success(request, 'Data tendik berhasil diperbarui.')
            return redirect('simda_dosen:daftar_tendik')
    else:
        form = DataTendikForm(instance=tendik)
    return render(request, 'simda_dosen/tendik_form.html', {
        'form': form, 'judul': f'Ubah Data Tendik: {tendik.nama_lengkap}',
    })


@login_required
def toggle_aktif_tendik(request, tendik_id):
    """POST-only: aktifkan/nonaktifkan, BUKAN hapus -- data tendik
    terhubung ke riwayat presensi/jabatan struktural, penghapusan fisik
    berisiko merusak data historis. Field is_active sudah untuk ini."""
    if not _bisa_kelola_data_tendik(request.user):
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")
    if request.method != 'POST':
        return redirect('simda_dosen:daftar_tendik')

    tendik = get_object_or_404(DataTendik.objects.using('simda'), id=tendik_id)
    tendik.is_active = not tendik.is_active
    tendik.save(update_fields=['is_active'])
    messages.success(
        request, f"{tendik.nama_lengkap} sekarang {'aktif' if tendik.is_active else 'nonaktif'}.",
    )
    return redirect('simda_dosen:daftar_tendik')


# ============================================================
# Profil Tendik -- perluasan Kelola Data Tendik: biodata (sudah ada di
# atas) + Riwayat Pendidikan/Pelatihan/Prestasi (SIMDA, FK ke DataTendik,
# admin-only sama seperti Kelola Data Tendik, lihat
# tambah_tabel_riwayat_tendik.sql di repo SIMDA untuk skema tabelnya).
# ============================================================

@login_required
def detail_tendik(request, tendik_id):
    if not _bisa_kelola_data_tendik(request.user):
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")

    tendik = get_object_or_404(DataTendik.objects.using('simda'), id=tendik_id)
    context = {
        'tendik': tendik,
        'riwayat_pendidikan_list': tendik.riwayat_pendidikan.all(),
        'riwayat_pelatihan_list': tendik.riwayat_pelatihan.all(),
        'riwayat_prestasi_list': tendik.riwayat_prestasi.all(),
        'form_pendidikan': RiwayatPendidikanTendikForm(),
        'form_pelatihan': RiwayatPelatihanTendikForm(),
        'form_prestasi': RiwayatPrestasiTendikForm(),
        'mode_diri_sendiri': False,
    }
    return render(request, 'simda_dosen/detail_tendik.html', context)


@login_required
def profil_riwayat_saya(request):
    """Self-service Riwayat Pendidikan/Pelatihan/Prestasi milik sendiri
    untuk role tendik (2026-08-04) -- biodata TETAP admin-only lewat
    Kelola Data Tendik (keputusan user), yang dibuka cuma 3 riwayat ini.
    Dicocokkan ke DataTendik lewat nip_yayasan, sama pola dengan
    get_simda_dosen_or_none untuk dosen."""
    if request.user.role != 'tendik':
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")

    tendik = get_simda_tendik_or_none(request.user)
    if not tendik:
        messages.error(request, 'NIP Yayasan Anda belum cocok dengan data di SIMDA. Hubungi admin.')
        return redirect('dashboard:index')

    context = {
        'tendik': tendik,
        'riwayat_pendidikan_list': tendik.riwayat_pendidikan.all(),
        'riwayat_pelatihan_list': tendik.riwayat_pelatihan.all(),
        'riwayat_prestasi_list': tendik.riwayat_prestasi.all(),
        'form_pendidikan': RiwayatPendidikanTendikForm(),
        'form_pelatihan': RiwayatPelatihanTendikForm(),
        'form_prestasi': RiwayatPrestasiTendikForm(),
        'mode_diri_sendiri': True,
    }
    return render(request, 'simda_dosen/detail_tendik.html', context)


# ---- Riwayat Pendidikan ----

@login_required
def tambah_riwayat_pendidikan_tendik(request, tendik_id):
    if not _role_bisa_riwayat_tendik(request.user.role):
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")
    tendik = get_object_or_404(DataTendik.objects.using('simda'), id=tendik_id)
    if not _bisa_kelola_riwayat_tendik(request.user, tendik):
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")
    if request.method != 'POST':
        return _redirect_setelah_riwayat_tendik(request, tendik_id)

    form = RiwayatPendidikanTendikForm(request.POST, request.FILES)
    if form.is_valid():
        riwayat = form.save(commit=False)
        riwayat.tendik = tendik
        riwayat.save()
        messages.success(request, 'Riwayat pendidikan berhasil ditambahkan.')
    else:
        messages.error(request, 'Data riwayat pendidikan tidak valid, periksa kembali.')
    return _redirect_setelah_riwayat_tendik(request, tendik_id)


@login_required
def edit_riwayat_pendidikan_tendik(request, riwayat_id):
    if not _role_bisa_riwayat_tendik(request.user.role):
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")
    riwayat = get_object_or_404(RiwayatPendidikanTendik.objects.using('simda'), id=riwayat_id)
    if not _bisa_kelola_riwayat_tendik(request.user, riwayat.tendik):
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")
    if request.method == 'POST':
        form = RiwayatPendidikanTendikForm(request.POST, request.FILES, instance=riwayat)
        if form.is_valid():
            form.save()
            messages.success(request, 'Riwayat pendidikan berhasil diperbarui.')
            return _redirect_setelah_riwayat_tendik(request, riwayat.tendik_id)
    else:
        form = RiwayatPendidikanTendikForm(instance=riwayat)
    return render(request, 'simda_dosen/edit_riwayat_pendidikan_tendik.html', {
        'form': form, 'riwayat': riwayat,
    })


@login_required
def hapus_riwayat_pendidikan_tendik(request, riwayat_id):
    if not _role_bisa_riwayat_tendik(request.user.role):
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")
    riwayat = get_object_or_404(RiwayatPendidikanTendik.objects.using('simda'), id=riwayat_id)
    if not _bisa_kelola_riwayat_tendik(request.user, riwayat.tendik):
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")
    if request.method != 'POST':
        return _redirect_setelah_riwayat_tendik(request, riwayat.tendik_id)

    tendik_id = riwayat.tendik_id
    riwayat.delete()
    messages.success(request, 'Riwayat pendidikan berhasil dihapus.')
    return _redirect_setelah_riwayat_tendik(request, tendik_id)


# ---- Riwayat Pelatihan ----

@login_required
def tambah_riwayat_pelatihan_tendik(request, tendik_id):
    if not _role_bisa_riwayat_tendik(request.user.role):
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")
    tendik = get_object_or_404(DataTendik.objects.using('simda'), id=tendik_id)
    if not _bisa_kelola_riwayat_tendik(request.user, tendik):
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")
    if request.method != 'POST':
        return _redirect_setelah_riwayat_tendik(request, tendik_id)

    form = RiwayatPelatihanTendikForm(request.POST, request.FILES)
    if form.is_valid():
        riwayat = form.save(commit=False)
        riwayat.tendik = tendik
        riwayat.save()
        messages.success(request, 'Riwayat pelatihan berhasil ditambahkan.')
    else:
        messages.error(request, 'Data riwayat pelatihan tidak valid, periksa kembali.')
    return _redirect_setelah_riwayat_tendik(request, tendik_id)


@login_required
def edit_riwayat_pelatihan_tendik(request, riwayat_id):
    if not _role_bisa_riwayat_tendik(request.user.role):
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")
    riwayat = get_object_or_404(RiwayatPelatihanTendik.objects.using('simda'), id=riwayat_id)
    if not _bisa_kelola_riwayat_tendik(request.user, riwayat.tendik):
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")
    if request.method == 'POST':
        form = RiwayatPelatihanTendikForm(request.POST, request.FILES, instance=riwayat)
        if form.is_valid():
            form.save()
            messages.success(request, 'Riwayat pelatihan berhasil diperbarui.')
            return _redirect_setelah_riwayat_tendik(request, riwayat.tendik_id)
    else:
        form = RiwayatPelatihanTendikForm(instance=riwayat)
    return render(request, 'simda_dosen/edit_riwayat_pelatihan_tendik.html', {
        'form': form, 'riwayat': riwayat,
    })


@login_required
def hapus_riwayat_pelatihan_tendik(request, riwayat_id):
    if not _role_bisa_riwayat_tendik(request.user.role):
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")
    riwayat = get_object_or_404(RiwayatPelatihanTendik.objects.using('simda'), id=riwayat_id)
    if not _bisa_kelola_riwayat_tendik(request.user, riwayat.tendik):
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")
    if request.method != 'POST':
        return _redirect_setelah_riwayat_tendik(request, riwayat.tendik_id)

    tendik_id = riwayat.tendik_id
    riwayat.delete()
    messages.success(request, 'Riwayat pelatihan berhasil dihapus.')
    return _redirect_setelah_riwayat_tendik(request, tendik_id)


# ---- Riwayat Prestasi ----

@login_required
def tambah_riwayat_prestasi_tendik(request, tendik_id):
    if not _role_bisa_riwayat_tendik(request.user.role):
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")
    tendik = get_object_or_404(DataTendik.objects.using('simda'), id=tendik_id)
    if not _bisa_kelola_riwayat_tendik(request.user, tendik):
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")
    if request.method != 'POST':
        return _redirect_setelah_riwayat_tendik(request, tendik_id)

    form = RiwayatPrestasiTendikForm(request.POST, request.FILES)
    if form.is_valid():
        riwayat = form.save(commit=False)
        riwayat.tendik = tendik
        riwayat.save()
        messages.success(request, 'Riwayat prestasi berhasil ditambahkan.')
    else:
        messages.error(request, 'Data riwayat prestasi tidak valid, periksa kembali.')
    return _redirect_setelah_riwayat_tendik(request, tendik_id)


@login_required
def edit_riwayat_prestasi_tendik(request, riwayat_id):
    if not _role_bisa_riwayat_tendik(request.user.role):
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")
    riwayat = get_object_or_404(RiwayatPrestasiTendik.objects.using('simda'), id=riwayat_id)
    if not _bisa_kelola_riwayat_tendik(request.user, riwayat.tendik):
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")
    if request.method == 'POST':
        form = RiwayatPrestasiTendikForm(request.POST, request.FILES, instance=riwayat)
        if form.is_valid():
            form.save()
            messages.success(request, 'Riwayat prestasi berhasil diperbarui.')
            return _redirect_setelah_riwayat_tendik(request, riwayat.tendik_id)
    else:
        form = RiwayatPrestasiTendikForm(instance=riwayat)
    return render(request, 'simda_dosen/edit_riwayat_prestasi_tendik.html', {
        'form': form, 'riwayat': riwayat,
    })


@login_required
def hapus_riwayat_prestasi_tendik(request, riwayat_id):
    if not _role_bisa_riwayat_tendik(request.user.role):
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")
    riwayat = get_object_or_404(RiwayatPrestasiTendik.objects.using('simda'), id=riwayat_id)
    if not _bisa_kelola_riwayat_tendik(request.user, riwayat.tendik):
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")
    if request.method != 'POST':
        return _redirect_setelah_riwayat_tendik(request, riwayat.tendik_id)

    tendik_id = riwayat.tendik_id
    riwayat.delete()
    messages.success(request, 'Riwayat prestasi berhasil dihapus.')
    return _redirect_setelah_riwayat_tendik(request, tendik_id)
