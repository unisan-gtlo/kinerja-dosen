from django.contrib import admin

from .models import (
    LokasiKantor, JadwalKerja, Perangkat, EnrolmentWajah, Presensi,
    FotoPresensi, QRToken, IzinCuti, LogKecurangan,
)


@admin.register(LokasiKantor)
class LokasiKantorAdmin(admin.ModelAdmin):
    list_display = ['nama', 'radius_meter', 'jam_masuk', 'jam_pulang', 'wajib_qr', 'wajib_wifi', 'aktif']
    list_filter = ['aktif', 'wajib_qr', 'wajib_wifi']
    search_fields = ['nama']


@admin.register(JadwalKerja)
class JadwalKerjaAdmin(admin.ModelAdmin):
    list_display = ['nidn', 'lokasi', 'hari', 'jam_masuk', 'jam_pulang', 'aktif']
    list_filter = ['hari', 'aktif', 'lokasi']
    search_fields = ['nidn']


@admin.register(Perangkat)
class PerangkatAdmin(admin.ModelAdmin):
    list_display = ['nidn', 'device_id', 'platform', 'terpercaya', 'is_rooted', 'terakhir_dipakai']
    list_filter = ['platform', 'terpercaya', 'is_rooted']
    search_fields = ['nidn', 'device_id']


@admin.register(EnrolmentWajah)
class EnrolmentWajahAdmin(admin.ModelAdmin):
    # embedding_terenkripsi sengaja tidak ditampilkan/diedit lewat admin.
    list_display = ['nidn', 'versi_model', 'consent_disetujui', 'consent_pada']
    list_filter = ['consent_disetujui']
    search_fields = ['nidn']
    exclude = ['embedding_terenkripsi']
    readonly_fields = ['dibuat', 'diperbarui']


@admin.register(Presensi)
class PresensiAdmin(admin.ModelAdmin):
    list_display = ['nidn', 'tanggal', 'status', 'tingkat_risiko', 'ditandai', 'lokasi']
    list_filter = ['status', 'tingkat_risiko', 'ditandai', 'lokasi']
    search_fields = ['nidn']
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
    list_display = ['nidn', 'tipe', 'tanggal_mulai', 'tanggal_selesai', 'status']
    list_filter = ['tipe', 'status']
    search_fields = ['nidn']


@admin.register(LogKecurangan)
class LogKecuranganAdmin(admin.ModelAdmin):
    list_display = ['nidn', 'jenis_anomali', 'skor', 'waktu']
    list_filter = ['jenis_anomali']
    search_fields = ['nidn']
