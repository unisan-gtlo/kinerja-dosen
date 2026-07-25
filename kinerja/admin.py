from django.contrib import admin

from .models import Penghargaan, KegiatanPenunjang, DokumenKinerja
# Penelitian/Publikasi/HKI pindah ke app penelitian (lihat penelitian/admin.py).
# Pengabdian (PKM)/Pembicara/Pengelola Jurnal/Jabatan Struktural pindah ke
# app pengabdian (lihat pengabdian/admin.py).

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