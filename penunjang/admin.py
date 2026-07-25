from django.contrib import admin
from .models import AnggotaProfesi, Penghargaan, PenunjangLain, AnggotaPenunjangLain


@admin.register(AnggotaProfesi)
class AnggotaProfesiAdmin(admin.ModelAdmin):
    list_display = ['user', 'nama_organisasi', 'peran', 'mulai_keanggotaan']
    list_filter = ['kategori_kegiatan']
    search_fields = ['user__username', 'nama_organisasi']


@admin.register(Penghargaan)
class PenghargaanAdmin(admin.ModelAdmin):
    list_display = ['user', 'nama_penghargaan', 'tingkat_penghargaan', 'tahun']
    list_filter = ['tingkat_penghargaan', 'tahun']
    search_fields = ['user__username', 'nama_penghargaan']


@admin.register(PenunjangLain)
class PenunjangLainAdmin(admin.ModelAdmin):
    list_display = ['user', 'nama_kegiatan', 'jenis_kegiatan', 'tingkat', 'tanggal_mulai']
    list_filter = ['jenis_kegiatan', 'tingkat']
    search_fields = ['user__username', 'nama_kegiatan']


@admin.register(AnggotaPenunjangLain)
class AnggotaPenunjangLainAdmin(admin.ModelAdmin):
    list_display = ['penunjang_lain', 'nama', 'peran']
    search_fields = ['nama', 'penunjang_lain__nama_kegiatan']
