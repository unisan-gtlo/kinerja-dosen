from django.contrib import admin

from .models import (
    DataDosen, RiwayatJabatanFungsional, RiwayatPendidikanDosen, RiwayatBKD,
    FakultasPublik, ProdiPublik, TahunAkademikPublik,
    AgamaPublik, JabatanFungsionalPublik,
)


@admin.register(DataDosen)
class DataDosenAdmin(admin.ModelAdmin):
    list_display = ['nidn', 'nama_lengkap', 'kode_fakultas', 'kode_prodi', 'is_active']
    search_fields = ['nidn', 'nama_lengkap']
    list_filter = ['kode_fakultas', 'kode_prodi', 'is_active']


@admin.register(RiwayatJabatanFungsional)
class RiwayatJabatanFungsionalAdmin(admin.ModelAdmin):
    list_display = ['dosen', 'jabatan_fungsional_id', 'tmt', 'tgl_selesai']


@admin.register(RiwayatPendidikanDosen)
class RiwayatPendidikanDosenAdmin(admin.ModelAdmin):
    list_display = ['dosen', 'jenjang', 'institusi', 'tahun_lulus']


@admin.register(RiwayatBKD)
class RiwayatBKDAdmin(admin.ModelAdmin):
    list_display = ['dosen', 'periode_id', 'status_pengesahan', 'total_sks']
    list_filter = ['status_pengesahan']


@admin.register(FakultasPublik)
class FakultasPublikAdmin(admin.ModelAdmin):
    list_display = ['kode_fakultas', 'nama_fakultas', 'status']


@admin.register(ProdiPublik)
class ProdiPublikAdmin(admin.ModelAdmin):
    list_display = ['kode_prodi', 'nama_prodi', 'kode_fakultas', 'jenjang', 'status']


@admin.register(TahunAkademikPublik)
class TahunAkademikPublikAdmin(admin.ModelAdmin):
    list_display = ['tahun_akademik', 'semester_aktif', 'is_aktif']


@admin.register(AgamaPublik)
class AgamaPublikAdmin(admin.ModelAdmin):
    list_display = ['kode', 'nama', 'urutan']


@admin.register(JabatanFungsionalPublik)
class JabatanFungsionalPublikAdmin(admin.ModelAdmin):
    list_display = ['kode', 'nama', 'singkatan', 'urutan']
