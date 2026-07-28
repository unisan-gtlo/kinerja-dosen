"""
Model modul Presensi — Portal Kinerja UNISAN.

Tahap 2 (Model & DB), hasil audit repositori (lihat CLAUDE.md).

Catatan integrasi data dosen:
- Data dosen TIDAK diduplikasi di sini. Setiap tabel yang butuh dosen
  menyimpan field `nidn` (CharField biasa), BUKAN ForeignKey ke
  simda_dosen.DataDosen: sikd_db dan unisan_db adalah database Postgres
  yang berbeda, dan config/db_router.py::SimdaRouter.allow_relation()
  sengaja melarang relasi lintas-app ke simda_dosen (Postgres tidak
  mendukung FK/JOIN lintas database). Pola ini sama dengan yang sudah
  dipakai app `profil` (lihat simda_dosen/utils.py::get_simda_dosen_or_none).
- Untuk mengambil data dosen dari NIDN, pakai presensi.utils.get_dosen_by_nidn.
- Presensi hanya MEMBACA data dosen (read-only); jangan pernah menulis ke sana.

Catatan lokasi/geofence:
- Titik GPS disimpan sebagai `latitude`/`longitude` (FloatField) biasa, BUKAN
  PostGIS PointField: GDAL native library tidak tersedia di lingkungan dev
  proyek ini, dan django.contrib.gis butuh GDAL hanya untuk diimpor. Jarak ke
  LokasiKantor dihitung dengan formula Haversine (lihat presensi/geo.py),
  yang cukup akurat untuk geofence berskala ratusan meter.
"""
from datetime import time

from django.db import models
from django.utils import timezone

from .utils import get_dosen_by_nidn


class StatusPresensi(models.TextChoices):
    HADIR = "hadir", "Hadir"
    TELAT = "telat", "Terlambat"
    IZIN = "izin", "Izin/Cuti"
    ALPA = "alpa", "Alpa"
    DITOLAK = "ditolak", "Ditolak (anomali)"


class TingkatRisiko(models.TextChoices):
    RENDAH = "rendah", "Rendah — otomatis sah"
    SEDANG = "sedang", "Sedang — ditandai untuk tinjauan HR"
    TINGGI = "tinggi", "Tinggi — ditolak"


class LokasiKantor(models.Model):
    """Titik kantor/kampus + geofence. Mendukung banyak lokasi."""
    nama = models.CharField("Nama lokasi", max_length=150)
    latitude = models.FloatField("Latitude titik pusat")
    longitude = models.FloatField("Longitude titik pusat")
    radius_meter = models.PositiveIntegerField("Radius geofence (meter)", default=100)

    jam_masuk = models.TimeField(default=time(8, 0))
    jam_pulang = models.TimeField(default=time(16, 0))
    toleransi_menit = models.PositiveIntegerField("Toleransi telat (menit)", default=15)
    timezone = models.CharField(max_length=64, default="Asia/Makassar")

    # ---- Opsi tambahan (feature flag per lokasi, default MATI) ----
    wajib_qr = models.BooleanField("Wajibkan scan QR", default=False)
    wajib_wifi = models.BooleanField("Wajibkan Wi-Fi/IP kantor", default=False)
    ssid_wifi = models.CharField("SSID Wi-Fi kantor", max_length=100, blank=True)
    ip_jaringan = models.CharField("Rentang IP kantor (CIDR)", max_length=64, blank=True)

    aktif = models.BooleanField(default=True)
    dibuat = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Lokasi Kantor"
        verbose_name_plural = "Lokasi Kantor"

    def __str__(self):
        return f"{self.nama} (r={self.radius_meter}m)"


class JadwalKerja(models.Model):
    """Jadwal per dosen atau default per lokasi. Sederhana; bisa diperluas ke shift."""
    nidn = models.CharField("NIDN Dosen", max_length=20, db_index=True, blank=True)
    lokasi = models.ForeignKey(LokasiKantor, on_delete=models.PROTECT, related_name="jadwal")
    hari = models.PositiveSmallIntegerField("Hari (0=Senin..6=Minggu)", default=0)
    jam_masuk = models.TimeField(default=time(8, 0))
    jam_pulang = models.TimeField(default=time(16, 0))
    aktif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Jadwal Kerja"
        verbose_name_plural = "Jadwal Kerja"

    @property
    def dosen(self):
        return get_dosen_by_nidn(self.nidn)


class Perangkat(models.Model):
    """Device binding: 1 akun terikat perangkat terdaftar."""
    nidn = models.CharField("NIDN Dosen", max_length=20, db_index=True)
    device_id = models.CharField("ID perangkat", max_length=200)
    platform = models.CharField(max_length=40, blank=True)  # android/ios/web
    terpercaya = models.BooleanField("Disetujui admin", default=False)
    is_rooted = models.BooleanField("Terdeteksi root/emulator", default=False)
    terakhir_dipakai = models.DateTimeField(null=True, blank=True)
    dibuat = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Perangkat"
        verbose_name_plural = "Perangkat"
        unique_together = ("nidn", "device_id")

    @property
    def dosen(self):
        return get_dosen_by_nidn(self.nidn)


class EnrolmentWajah(models.Model):
    """
    Data biometrik. Simpan EMBEDDING TERENKRIPSI, bukan foto mentah.
    Enkripsi memakai kunci di env (mis. FIELD_ENCRYPTION_KEY / Fernet).
    """
    nidn = models.CharField("NIDN Dosen", max_length=20, unique=True, db_index=True)
    embedding_terenkripsi = models.BinaryField("Embedding wajah (terenkripsi)")
    versi_model = models.CharField(max_length=40, blank=True)  # mis. arcface-r100
    consent_disetujui = models.BooleanField("Persetujuan biometrik (UU PDP)", default=False)
    consent_pada = models.DateTimeField(null=True, blank=True)
    dibuat = models.DateTimeField(auto_now_add=True)
    diperbarui = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Enrolment Wajah"
        verbose_name_plural = "Enrolment Wajah"

    @property
    def dosen(self):
        return get_dosen_by_nidn(self.nidn)


class Presensi(models.Model):
    """Satu baris = satu hari presensi seorang dosen (masuk + pulang)."""
    nidn = models.CharField("NIDN Dosen", max_length=20, db_index=True)
    tanggal = models.DateField(default=timezone.localdate)

    # Waktu SELALU dari server (bukan dari perangkat).
    waktu_masuk = models.DateTimeField(null=True, blank=True)
    waktu_pulang = models.DateTimeField(null=True, blank=True)

    lokasi = models.ForeignKey(LokasiKantor, on_delete=models.PROTECT, null=True, blank=True)
    latitude_masuk = models.FloatField(null=True, blank=True)
    longitude_masuk = models.FloatField(null=True, blank=True)
    latitude_pulang = models.FloatField(null=True, blank=True)
    longitude_pulang = models.FloatField(null=True, blank=True)
    akurasi_masuk_m = models.FloatField(null=True, blank=True)

    status = models.CharField(max_length=10, choices=StatusPresensi.choices, default=StatusPresensi.HADIR)
    skor_risiko = models.PositiveSmallIntegerField(default=0)   # 0..100
    tingkat_risiko = models.CharField(max_length=10, choices=TingkatRisiko.choices, default=TingkatRisiko.RENDAH)
    ditandai = models.BooleanField("Perlu tinjauan HR", default=False)

    dibuat = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Presensi"
        verbose_name_plural = "Presensi"
        unique_together = ("nidn", "tanggal")
        indexes = [models.Index(fields=["tanggal", "status"])]

    def __str__(self):
        return f"{self.nidn} · {self.tanggal} · {self.status}"

    @property
    def dosen(self):
        return get_dosen_by_nidn(self.nidn)


class FotoPresensi(models.Model):
    """Bukti selfie + skor verifikasi wajah. Simpan dengan retensi terbatas & terenkripsi."""
    class Tipe(models.TextChoices):
        MASUK = "masuk", "Masuk"
        PULANG = "pulang", "Pulang"

    presensi = models.ForeignKey(Presensi, on_delete=models.CASCADE, related_name="foto")
    tipe = models.CharField(max_length=6, choices=Tipe.choices)
    berkas = models.FileField(upload_to="presensi/selfie/%Y/%m/", blank=True)
    face_match_score = models.FloatField(null=True, blank=True)   # 0..1
    liveness_score = models.FloatField(null=True, blank=True)     # 0..1
    verified = models.BooleanField(default=False)
    dibuat = models.DateTimeField(auto_now_add=True)


class QRToken(models.Model):
    """Token QR dinamis, sekali pakai, berumur pendek (opsi)."""
    lokasi = models.ForeignKey(LokasiKantor, on_delete=models.CASCADE, related_name="qr_token")
    kode = models.CharField(max_length=64, unique=True)
    dibuat = models.DateTimeField(auto_now_add=True)
    kedaluwarsa = models.DateTimeField()
    dipakai = models.BooleanField(default=False)

    def masih_berlaku(self):
        return (not self.dipakai) and timezone.now() < self.kedaluwarsa


class IzinCuti(models.Model):
    class Tipe(models.TextChoices):
        IZIN = "izin", "Izin"
        SAKIT = "sakit", "Sakit"
        CUTI = "cuti", "Cuti"
        DINAS = "dinas", "Dinas Luar"

    class StatusApproval(models.TextChoices):
        MENUNGGU = "menunggu", "Menunggu"
        DISETUJUI = "disetujui", "Disetujui"
        DITOLAK = "ditolak", "Ditolak"

    nidn = models.CharField("NIDN Dosen", max_length=20, db_index=True)
    tipe = models.CharField(max_length=6, choices=Tipe.choices)
    tanggal_mulai = models.DateField()
    tanggal_selesai = models.DateField()
    alasan = models.TextField(blank=True)
    lampiran = models.FileField(upload_to="presensi/izin/%Y/%m/", blank=True)
    status = models.CharField(max_length=10, choices=StatusApproval.choices, default=StatusApproval.MENUNGGU)
    # approver bisa merujuk user portal kinerja; sesuaikan saat audit.
    approver = models.CharField("NIDN/ID atasan", max_length=50, blank=True)
    dibuat = models.DateTimeField(auto_now_add=True)

    @property
    def dosen(self):
        return get_dosen_by_nidn(self.nidn)


class LogKecurangan(models.Model):
    """Catatan anomali/kecurangan untuk audit & tinjauan."""
    nidn = models.CharField("NIDN Dosen", max_length=20, db_index=True)
    presensi = models.ForeignKey(Presensi, on_delete=models.SET_NULL, null=True, blank=True)
    jenis_anomali = models.CharField(max_length=100)   # mis. "mock_location", "wajah_tidak_cocok"
    detail = models.JSONField(default=dict, blank=True)
    skor = models.PositiveSmallIntegerField(default=0)
    waktu = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Log Kecurangan"
        verbose_name_plural = "Log Kecurangan"

    @property
    def dosen(self):
        return get_dosen_by_nidn(self.nidn)
