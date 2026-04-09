from django.contrib import admin
from .models import Fakultas, Prodi, TahunAkademik, Pengaturan

@admin.register(Fakultas)
class FakultasAdmin(admin.ModelAdmin):
    list_display = ['kode_fakultas', 'nama_fakultas', 'nama_dekan', 'status']
    search_fields = ['kode_fakultas', 'nama_fakultas']

@admin.register(Prodi)
class ProdiAdmin(admin.ModelAdmin):
    list_display = ['kode_prodi', 'nama_prodi', 'fakultas', 'jenjang', 'status']
    list_filter = ['fakultas', 'jenjang', 'status']
    search_fields = ['kode_prodi', 'nama_prodi']

@admin.register(TahunAkademik)
class TahunAkademikAdmin(admin.ModelAdmin):
    list_display = ['tahun_akademik', 'keterangan', 'urutan', 'status']
    ordering = ['-urutan']

@admin.register(Pengaturan)
class PengaturanAdmin(admin.ModelAdmin):
    list_display = ['status_input', 'deadline', 'ts_tahun', 'ts1_tahun', 'ts2_tahun']