from django.db.models import Count
from .models import DokumenKinerja


def attach_dokumen_count(items, jenis_kinerja):
    """Nempelin .jumlah_dokumen ke tiap objek di `items` (list/queryset/
    Page.object_list) berdasarkan DokumenKinerja yang sudah diunggah,
    supaya tombol Dokumen bisa tampilkan jumlahnya tanpa query per baris."""
    items = list(items)
    ids = [o.id for o in items]
    if not ids:
        return items
    counts = dict(
        DokumenKinerja.objects.filter(jenis_kinerja=jenis_kinerja, kinerja_id__in=ids)
        .values('kinerja_id').annotate(n=Count('id')).values_list('kinerja_id', 'n')
    )
    for o in items:
        o.jumlah_dokumen = counts.get(o.id, 0)
    return items
