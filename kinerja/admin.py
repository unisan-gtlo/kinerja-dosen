from django.contrib import admin
from .models import Penelitian, Publikasi, PKM, HKI

@admin.register(Penelitian)
class PenelitianAdmin(admin.ModelAdmin):
    list_display = ['user', 'judul', 'tahun_akademik', 'jenis_hibah', 'pendanaan']
    list_filter = ['tahun_akademik', 'ln_i']
    search_fields = ['user__username', 'judul']

@admin.register(Publikasi)
class PublikasiAdmin(admin.ModelAdmin):
    list_display = ['user', 'judul', 'jenis_publikasi', 'nama_jurnal', 'tahun_akademik']
    list_filter = ['jenis_publikasi', 'tahun_akademik']
    search_fields = ['user__username', 'judul']

@admin.register(PKM)
class PKMAdmin(admin.ModelAdmin):
    list_display = ['user', 'judul', 'tahun_akademik', 'jenis_hibah', 'pendanaan']
    list_filter = ['tahun_akademik', 'ln_i']
    search_fields = ['user__username', 'judul']

@admin.register(HKI)
class HKIAdmin(admin.ModelAdmin):
    list_display = ['user', 'judul', 'jenis_hki', 'tahun_akademik', 'no_hki']
    list_filter = ['jenis_hki', 'tahun_akademik']
    search_fields = ['user__username', 'judul']