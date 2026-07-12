from django.contrib import admin

from .models import PKM, Penghargaan, KegiatanPenunjang, DokumenKinerja
# Penelitian/Publikasi/HKI pindah ke app penelitian (lihat penelitian/admin.py).

@admin.register(PKM)
class PKMAdmin(admin.ModelAdmin):
    list_display = ['user', 'judul', 'tahun_akademik', 'jenis_hibah', 'pendanaan']
    list_filter = ['tahun_akademik', 'ln_i']
    search_fields = ['user__username', 'judul']

@admin.register(Penghargaan)
class PenghargaanAdmin(admin.ModelAdmin):
    list_display = ['user', 'nama_penghargaan', 'tingkat', 'tahun_akademik']
    list_filter = ['tingkat', 'tahun_akademik']
    search_fields = ['user__username', 'nama_penghargaan']

@admin.register(KegiatanPenunjang)
class KegiatanPenunjangAdmin(admin.ModelAdmin):
    list_display = ['user', 'jenis_kegiatan', 'nama_kegiatan', 'tahun_akademik']
    list_filter = ['jenis_kegiatan', 'tahun_akademik']
    search_fields = ['user__username', 'nama_kegiatan']

@admin.register(DokumenKinerja)
class DokumenKinerjaAdmin(admin.ModelAdmin):
    list_display = ['user', 'jenis_kinerja', 'jenis_dokumen', 'nama_dokumen', 'tersedia', 'tgl_input']
    list_filter = ['jenis_kinerja', 'jenis_dokumen']
    search_fields = ['user__username', 'nama_dokumen']