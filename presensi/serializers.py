from rest_framework import serializers


class AbsenSerializer(serializers.Serializer):
    """Dipakai untuk POST /api/presensi/masuk dan /api/presensi/pulang.

    Sekarang wajib multipart (ada `selfie`) karena syarat 2 (verifikasi
    wajah) sudah aktif -- lihat presensi/decision.py::verifikasi_wajah.
    Field qr_token, ssid/ip belum dipakai (menyusul saat opsi QR/Wi-Fi
    diaktifkan, lihat docs/presensi/spesifikasiapipresensi.md).
    """
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lng = serializers.FloatField(min_value=-180, max_value=180)
    akurasi_m = serializers.FloatField(min_value=0)
    device_id = serializers.CharField(max_length=200)
    selfie = serializers.ImageField()
    # Cuma relevan untuk /pulang -- wajib diisi kalau lembur di atas ambang
    # (lihat presensi.models.BATAS_MENIT_LEMBUR_WAJIB_KETERANGAN), diabaikan
    # untuk /masuk.
    keterangan_lembur = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")


class EnrolmentWajahSerializer(serializers.Serializer):
    """Dipakai untuk POST /api/presensi/enrolment-wajah -- pendaftaran wajah
    sekali di awal, sebelum dosen bisa lolos syarat 2 saat absen."""
    foto = serializers.ListField(
        child=serializers.ImageField(), min_length=2, max_length=5,
    )
    consent = serializers.BooleanField()

    def validate_consent(self, value):
        if not value:
            raise serializers.ValidationError(
                "Persetujuan pemrosesan data wajah (consent) wajib disetujui untuk mendaftarkan wajah."
            )
        return value


class ParafSerializer(serializers.Serializer):
    """Dipakai untuk POST /api/presensi/paraf -- simpan/ganti paraf
    digital (gambar hasil canvas, dikirim sebagai file PNG biasa)."""
    gambar = serializers.ImageField()
