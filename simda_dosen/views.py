from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from .models import MataKuliahPublik, MahasiswaPublik, DataDosen


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
