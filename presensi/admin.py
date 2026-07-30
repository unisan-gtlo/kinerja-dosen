from django.contrib import admin

from .models import (
    LokasiKantor, KelompokPresensi, TargetKerjaBulanan, HariLibur, JadwalKerja, Perangkat, EnrolmentWajah,
    ParafDosen, Presensi, FotoPresensi, QRToken, IzinCuti, LogKecurangan,
)


@admin.register(LokasiKantor)
class LokasiKantorAdmin(admin.ModelAdmin):
    list_display = ['nama', 'radius_meter', 'jam_masuk', 'jam_pulang', 'wajib_qr', 'wajib_wifi', 'aktif']
    list_filter = ['aktif', 'wajib_qr', 'wajib_wifi']
    search_fields = ['nama']


@admin.register(KelompokPresensi)
class KelompokPresensiAdmin(admin.ModelAdmin):
    list_display = ['nama', 'roles', 'jam_masuk', 'jam_pulang', 'toleransi_menit', 'aktif']
    list_filter = ['aktif']
    search_fields = ['nama']


@admin.register(TargetKerjaBulanan)
class TargetKerjaBulananAdmin(admin.ModelAdmin):
    list_display = ['kelompok', 'bulan', 'tahun', 'target_hari_kerja', 'target_jam_kerja']
    list_filter = ['kelompok', 'tahun']


@admin.register(HariLibur)
class HariLiburAdmin(admin.ModelAdmin):
    list_display = ['tanggal', 'keterangan', 'jenis']
    list_filter = ['jenis']
    search_fields = ['keterangan']
    date_hierarchy = 'tanggal'


@admin.register(JadwalKerja)
class JadwalKerjaAdmin(admin.ModelAdmin):
    list_display = ['user', 'lokasi', 'hari', 'jam_masuk', 'jam_pulang', 'aktif']
    list_filter = ['hari', 'aktif', 'lokasi']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'user__nidn']


@admin.register(Perangkat)
class PerangkatAdmin(admin.ModelAdmin):
    list_display = ['user', 'device_id', 'platform', 'terpercaya', 'is_rooted', 'terakhir_dipakai']
    list_filter = ['platform', 'terpercaya', 'is_rooted']
    search_fields = ['user__username', 'user__nidn', 'device_id']


@admin.register(EnrolmentWajah)
class EnrolmentWajahAdmin(admin.ModelAdmin):
    # embedding_terenkripsi sengaja tidak ditampilkan/diedit lewat admin.
    list_display = ['user', 'versi_model', 'consent_disetujui', 'consent_pada']
    list_filter = ['consent_disetujui']
    search_fields = ['user__username', 'user__nidn']
    exclude = ['embedding_terenkripsi']
    readonly_fields = ['dibuat', 'diperbarui']


@admin.register(ParafDosen)
class ParafDosenAdmin(admin.ModelAdmin):
    list_display = ['user', 'dibuat', 'diperbarui']
    search_fields = ['user__username', 'user__nidn']
    readonly_fields = ['dibuat', 'diperbarui']


@admin.register(Presensi)
class PresensiAdmin(admin.ModelAdmin):
    list_display = ['user', 'tanggal', 'status', 'tingkat_risiko', 'ditandai', 'lokasi', 'kelompok']
    list_filter = ['status', 'tingkat_risiko', 'ditandai', 'lokasi', 'kelompok']
    search_fields = ['user__username', 'user__nidn']
    date_hierarchy = 'tanggal'


@admin.register(FotoPresensi)
class FotoPresensiAdmin(admin.ModelAdmin):
    list_display = ['presensi', 'tipe', 'face_match_score', 'liveness_score', 'verified']
    list_filter = ['tipe', 'verified']


@admin.register(QRToken)
class QRTokenAdmin(admin.ModelAdmin):
    list_display = ['lokasi', 'kode', 'kedaluwarsa', 'dipakai']
    list_filter = ['dipakai', 'lokasi']


@admin.register(IzinCuti)
class IzinCutiAdmin(admin.ModelAdmin):
    list_display = ['user', 'tipe', 'tanggal_mulai', 'tanggal_selesai', 'status']
    list_filter = ['tipe', 'status']
    search_fields = ['user__username', 'user__nidn']


@admin.register(LogKecurangan)
class LogKecuranganAdmin(admin.ModelAdmin):
    list_display = ['user', 'jenis_anomali', 'skor', 'waktu']
    list_filter = ['jenis_anomali']
    search_fields = ['user__username', 'user__nidn']
