from rest_framework import serializers


class AbsenSerializer(serializers.Serializer):
    """Dipakai untuk POST /api/presensi/masuk dan /api/presensi/pulang.

    MVP ini hanya mengaktifkan syarat 1 (cek lokasi) — field selfie,
    qr_token, ssid/ip belum dipakai (menyusul saat verifikasi wajah & opsi
    QR/Wi-Fi diaktifkan, lihat docs/presensi/spesifikasiapipresensi.md).
    """
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lng = serializers.FloatField(min_value=-180, max_value=180)
    akurasi_m = serializers.FloatField(min_value=0)
    device_id = serializers.CharField(max_length=200)
