from django.contrib import admin

from .models import DokumenKinerja
# Penelitian/Publikasi/HKI pindah ke app penelitian (lihat penelitian/admin.py).
# Pengabdian (PKM)/Pembicara/Pengelola Jurnal/Jabatan Struktural pindah ke
# app pengabdian (lihat pengabdian/admin.py).
# Penghargaan/Kegiatan Penunjang/Anggota Profesi pindah ke app penunjang
# (lihat penunjang/admin.py).

@admin.register(DokumenKinerja)
class DokumenKinerjaAdmin(admin.ModelAdmin):
    list_display = ['user', 'jenis_kinerja', 'jenis_dokumen', 'nama_dokumen', 'tersedia', 'tgl_input']
    list_filter = ['jenis_kinerja', 'jenis_dokumen']
    search_fields = ['user__username', 'nama_dokumen']