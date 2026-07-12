from django.contrib import admin
from .models import (
    Pengajaran, BimbinganMahasiswa, PengujianMahasiswa, BahanAjar,
    PembinaanMahasiswa, OrasiIlmiah, TugasTambahan,
)


@admin.register(Pengajaran)
class PengajaranAdmin(admin.ModelAdmin):
    list_display = ['user', 'nama_mk', 'nama_kelas', 'tahun_akademik']
    list_filter = ['tahun_akademik']
    search_fields = ['user__username', 'nama_mk', 'kode_mk']


@admin.register(BimbinganMahasiswa)
class BimbinganMahasiswaAdmin(admin.ModelAdmin):
    list_display = ['user', 'nama_mahasiswa', 'jenis_bimbingan', 'kategori', 'tahun_akademik']
    list_filter = ['jenis_bimbingan', 'kategori', 'tahun_akademik']
    search_fields = ['user__username', 'nama_mahasiswa', 'nim']


@admin.register(PengujianMahasiswa)
class PengujianMahasiswaAdmin(admin.ModelAdmin):
    list_display = ['user', 'nama_mahasiswa', 'kategori', 'tahun_akademik']
    list_filter = ['kategori', 'tahun_akademik']
    search_fields = ['user__username', 'nama_mahasiswa', 'nim']


@admin.register(BahanAjar)
class BahanAjarAdmin(admin.ModelAdmin):
    list_display = ['user', 'judul', 'jenis_bahan_ajar', 'tahun_terbit']
    list_filter = ['jenis_bahan_ajar', 'tahun_terbit']
    search_fields = ['user__username', 'judul']


@admin.register(PembinaanMahasiswa)
class PembinaanMahasiswaAdmin(admin.ModelAdmin):
    list_display = ['user', 'nama_kegiatan', 'jenis_kegiatan', 'tingkat', 'tahun']
    list_filter = ['jenis_kegiatan', 'tingkat', 'tahun']
    search_fields = ['user__username', 'nama_kegiatan']


@admin.register(OrasiIlmiah)
class OrasiIlmiahAdmin(admin.ModelAdmin):
    list_display = ['user', 'judul_orasi', 'tingkat', 'tanggal']
    list_filter = ['tingkat']
    search_fields = ['user__username', 'judul_orasi']


@admin.register(TugasTambahan)
class TugasTambahanAdmin(admin.ModelAdmin):
    list_display = ['user', 'jabatan_tambahan', 'tanggal_mulai', 'tanggal_selesai']
    search_fields = ['user__username', 'jabatan_tambahan']
