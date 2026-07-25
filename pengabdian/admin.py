from django.contrib import admin
from .models import (
    Pengabdian, AnggotaPengabdian, Pembicara, PengelolaJurnal, JabatanStruktural,
)


@admin.register(Pengabdian)
class PengabdianAdmin(admin.ModelAdmin):
    list_display = ['user', 'judul_kegiatan', 'kategori_kegiatan', 'tahun_kegiatan']
    list_filter = ['kategori_kegiatan', 'tahun_kegiatan']
    search_fields = ['user__username', 'judul_kegiatan']


@admin.register(AnggotaPengabdian)
class AnggotaPengabdianAdmin(admin.ModelAdmin):
    list_display = ['pengabdian', 'jenis_anggota', 'nama', 'peran', 'status_aktif']
    list_filter = ['jenis_anggota', 'peran', 'status_aktif']
    search_fields = ['nama', 'pengabdian__judul_kegiatan']


@admin.register(Pembicara)
class PembicaraAdmin(admin.ModelAdmin):
    list_display = ['user', 'judul_makalah', 'nama_pertemuan_ilmiah', 'tanggal_pelaksanaan']
    list_filter = ['kategori_kegiatan', 'tanggal_pelaksanaan']
    search_fields = ['user__username', 'judul_makalah', 'nama_pertemuan_ilmiah']


@admin.register(PengelolaJurnal)
class PengelolaJurnalAdmin(admin.ModelAdmin):
    list_display = ['user', 'nama_jurnal', 'peran', 'status_aktif']
    list_filter = ['status_aktif']
    search_fields = ['user__username', 'nama_jurnal']


@admin.register(JabatanStruktural)
class JabatanStrukturalAdmin(admin.ModelAdmin):
    list_display = ['user', 'jabatan_tugas', 'terhitung_mulai_tanggal', 'terhitung_selesai_tanggal']
    list_filter = ['terhitung_mulai_tanggal']
    search_fields = ['user__username', 'jabatan_tugas']
