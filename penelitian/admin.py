from django.contrib import admin
from .models import (
    Penelitian, AnggotaPenelitian, PublikasiKarya, PenulisPublikasiKarya,
    PatenHki, PenulisPatenHki,
)


@admin.register(Penelitian)
class PenelitianAdmin(admin.ModelAdmin):
    list_display = ['user', 'judul_kegiatan', 'kategori_pelaksanaan', 'tahun_kegiatan']
    list_filter = ['kategori_pelaksanaan', 'tahun_kegiatan']
    search_fields = ['user__username', 'judul_kegiatan']


@admin.register(AnggotaPenelitian)
class AnggotaPenelitianAdmin(admin.ModelAdmin):
    list_display = ['penelitian', 'jenis_anggota', 'nama', 'peran', 'status_aktif']
    list_filter = ['jenis_anggota', 'peran', 'status_aktif']
    search_fields = ['nama', 'penelitian__judul_kegiatan']


@admin.register(PublikasiKarya)
class PublikasiKaryaAdmin(admin.ModelAdmin):
    list_display = ['user', 'judul_artikel', 'jenis', 'tanggal_terbit']
    list_filter = ['jenis', 'tanggal_terbit']
    search_fields = ['user__username', 'judul_artikel']


@admin.register(PenulisPublikasiKarya)
class PenulisPublikasiKaryaAdmin(admin.ModelAdmin):
    list_display = ['publikasi', 'jenis_penulis', 'nama', 'peran', 'corresponding_author']
    list_filter = ['jenis_penulis', 'peran']
    search_fields = ['nama', 'publikasi__judul_artikel']


@admin.register(PatenHki)
class PatenHkiAdmin(admin.ModelAdmin):
    list_display = ['user', 'judul_karya', 'jenis', 'tanggal']
    list_filter = ['jenis', 'tanggal']
    search_fields = ['user__username', 'judul_karya']


@admin.register(PenulisPatenHki)
class PenulisPatenHkiAdmin(admin.ModelAdmin):
    list_display = ['paten_hki', 'jenis_penulis', 'nama', 'peran', 'corresponding_author']
    list_filter = ['jenis_penulis', 'peran']
    search_fields = ['nama', 'paten_hki__judul_karya']
