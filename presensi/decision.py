"""Mesin keputusan presensi.

Dirancang modular per syarat: MVP ini baru mengaktifkan **Cek Lokasi**
(syarat 1). Verifikasi Wajah (syarat 2), opsi QR, dan opsi Wi-Fi menyusul —
tambahkan fungsi cek baru di sini dan panggil dari presensi/views.py, tanpa
perlu mengubah cara syarat lokasi bekerja.

Catatan penting: karena syarat 2 (wajah) belum aktif, hasil "lolos cek
lokasi" TIDAK langsung dianggap presensi final/terverifikasi penuh sesuai
aturan gerbang-DAN di CLAUDE.md. Presensi tetap dibuat (supaya MVP bisa
dicoba), tapi ditandai tingkat_risiko=SEDANG + ditandai=True untuk tinjauan
HR, sampai syarat wajah ditambahkan.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from .geo import jarak_meter
from .models import LokasiKantor, StatusPresensi

AKURASI_GPS_MAKSIMAL_M = 50


@dataclass
class HasilCekLokasi:
    lolos: bool
    alasan: Optional[str]
    lokasi: Optional[LokasiKantor]
    jarak_m: Optional[float]


def cek_lokasi(lat, lng, akurasi_m) -> HasilCekLokasi:
    """Syarat 1: titik GPS harus di dalam radius geofence salah satu
    LokasiKantor aktif, dengan akurasi GPS yang cukup baik (akurasi buruk
    adalah indikasi umum mock-location)."""
    if akurasi_m is None or akurasi_m > AKURASI_GPS_MAKSIMAL_M:
        return HasilCekLokasi(False, "akurasi_buruk", None, None)

    lokasi_terpilih = None
    jarak_terdekat = None
    for lokasi in LokasiKantor.objects.filter(aktif=True):
        jarak = jarak_meter(lat, lng, lokasi.latitude, lokasi.longitude)
        if jarak <= lokasi.radius_meter and (jarak_terdekat is None or jarak < jarak_terdekat):
            lokasi_terpilih = lokasi
            jarak_terdekat = jarak

    if lokasi_terpilih is None:
        return HasilCekLokasi(False, "di_luar_radius", None, None)

    return HasilCekLokasi(True, None, lokasi_terpilih, jarak_terdekat)


def tentukan_status_waktu(lokasi: LokasiKantor, jam_saat_ini) -> str:
    """hadir vs telat, berdasarkan jam_masuk + toleransi_menit lokasi."""
    batas_telat = (
        datetime.combine(datetime.min, lokasi.jam_masuk) + timedelta(minutes=lokasi.toleransi_menit)
    ).time()
    return StatusPresensi.TELAT if jam_saat_ini > batas_telat else StatusPresensi.HADIR
