from django.contrib import admin
from .models import ProfilDosen, RiwayatJabfung, RiwayatPendidikan, Sertifikat, DokumenLain, BKD
@admin.register(ProfilDosen)
class ProfilDosenAdmin(admin.ModelAdmin):
    list_display = ['user', 'jabfung_aktif', 'pendidikan_terakhir', 'persentase_kelengkapan']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']

@admin.register(RiwayatJabfung)
class RiwayatJabfungAdmin(admin.ModelAdmin):
    list_display = ['user', 'jabatan', 'no_sk', 'tgl_sk', 'status']
    list_filter = ['jabatan', 'status']

@admin.register(RiwayatPendidikan)
class RiwayatPendidikanAdmin(admin.ModelAdmin):
    list_display = ['user', 'jenjang', 'bidang_ilmu', 'nama_pt', 'tahun_lulus']
    list_filter = ['jenjang']

@admin.register(Sertifikat)
class SertifikatAdmin(admin.ModelAdmin):
    list_display = ['user', 'jenis_sertifikat', 'nama_sertifikat', 'tahun_terbit']
    list_filter = ['jenis_sertifikat']

@admin.register(DokumenLain)
class DokumenLainAdmin(admin.ModelAdmin):
    list_display = ['user', 'jenis_dokumen', 'nama_dokumen', 'tgl_terbit']

@admin.register(BKD)
class BKDAdmin(admin.ModelAdmin):
    list_display = ['user', 'semester', 'tahun_akademik', 'bukti_tersedia', 'tgl_input']
    list_filter = ['semester', 'tahun_akademik']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']