from django.contrib import admin

from .models import Penelitian, Publikasi, PKM, HKI, Pengajaran, Penghargaan, KegiatanPenunjang, DokumenKinerja
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



@admin.register(Pengajaran)
class PengajaranAdmin(admin.ModelAdmin):
    list_display = ['user', 'jenis_kegiatan', 'nama_kegiatan', 'tahun_akademik']
    list_filter = ['jenis_kegiatan', 'tahun_akademik']
    search_fields = ['user__username', 'nama_kegiatan']

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