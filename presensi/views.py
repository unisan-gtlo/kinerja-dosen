from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from .decision import cek_lokasi, tentukan_status_waktu
from .models import LogKecurangan, Perangkat, Presensi, TingkatRisiko
from .serializers import AbsenSerializer

# Skor risiko sementara untuk presensi yang lolos cek lokasi (syarat 1),
# selama syarat 2 (verifikasi wajah) belum aktif -- lihat presensi/decision.py.
SKOR_RISIKO_LOKASI_SAJA = 40
SKOR_ANOMALI_LOKASI = 70


class PresensiRateThrottle(UserRateThrottle):
    scope = "presensi"


def _catat_perangkat(nidn, device_id, waktu):
    Perangkat.objects.update_or_create(
        nidn=nidn, device_id=device_id,
        defaults={"terakhir_dipakai": waktu},
    )


class AbsenMasukView(APIView):
    """POST /api/presensi/masuk — absen masuk, cek lokasi (syarat 1)."""
    throttle_classes = [PresensiRateThrottle]

    def post(self, request):
        serializer = AbsenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        nidn = request.user.nidn
        if not nidn:
            return Response(
                {"diterima": False, "alasan": "nidn_tidak_terdaftar"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        waktu_server = timezone.localtime(timezone.now())
        tanggal = waktu_server.date()

        if Presensi.objects.filter(nidn=nidn, tanggal=tanggal, waktu_masuk__isnull=False).exists():
            return Response(
                {"diterima": False, "alasan": "sudah_absen_masuk"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        _catat_perangkat(nidn, data["device_id"], waktu_server)

        hasil = cek_lokasi(data["lat"], data["lng"], data["akurasi_m"])
        if not hasil.lolos:
            LogKecurangan.objects.create(
                nidn=nidn,
                jenis_anomali=hasil.alasan,
                skor=SKOR_ANOMALI_LOKASI,
                detail={"lat": data["lat"], "lng": data["lng"], "akurasi_m": data["akurasi_m"]},
            )
            return Response({
                "diterima": False,
                "alasan": hasil.alasan,
                "tingkat_risiko": TingkatRisiko.TINGGI,
            })

        status_kehadiran = tentukan_status_waktu(hasil.lokasi, waktu_server.time())

        presensi, _ = Presensi.objects.update_or_create(
            nidn=nidn, tanggal=tanggal,
            defaults={
                "waktu_masuk": waktu_server,
                "lokasi": hasil.lokasi,
                "latitude_masuk": data["lat"],
                "longitude_masuk": data["lng"],
                "akurasi_masuk_m": data["akurasi_m"],
                "status": status_kehadiran,
                "skor_risiko": SKOR_RISIKO_LOKASI_SAJA,
                "tingkat_risiko": TingkatRisiko.SEDANG,
                "ditandai": True,
            },
        )

        return Response({
            "diterima": True,
            "status": presensi.status,
            "waktu_masuk": presensi.waktu_masuk,
            "lokasi": hasil.lokasi.nama,
            "skor_risiko": presensi.skor_risiko,
            "tingkat_risiko": presensi.tingkat_risiko,
        })


class AbsenPulangView(APIView):
    """POST /api/presensi/pulang — absen pulang, cek lokasi (syarat 1)."""
    throttle_classes = [PresensiRateThrottle]

    def post(self, request):
        serializer = AbsenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        nidn = request.user.nidn
        if not nidn:
            return Response(
                {"diterima": False, "alasan": "nidn_tidak_terdaftar"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        waktu_server = timezone.localtime(timezone.now())
        tanggal = waktu_server.date()

        try:
            presensi = Presensi.objects.get(nidn=nidn, tanggal=tanggal)
        except Presensi.DoesNotExist:
            return Response(
                {"diterima": False, "alasan": "belum_absen_masuk"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if presensi.waktu_pulang:
            return Response(
                {"diterima": False, "alasan": "sudah_absen_pulang"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        _catat_perangkat(nidn, data["device_id"], waktu_server)

        hasil = cek_lokasi(data["lat"], data["lng"], data["akurasi_m"])
        if not hasil.lolos:
            LogKecurangan.objects.create(
                nidn=nidn,
                presensi=presensi,
                jenis_anomali=hasil.alasan,
                skor=SKOR_ANOMALI_LOKASI,
                detail={"lat": data["lat"], "lng": data["lng"], "akurasi_m": data["akurasi_m"]},
            )
            return Response({
                "diterima": False,
                "alasan": hasil.alasan,
                "tingkat_risiko": TingkatRisiko.TINGGI,
            })

        presensi.waktu_pulang = waktu_server
        presensi.lokasi = presensi.lokasi or hasil.lokasi
        presensi.latitude_pulang = data["lat"]
        presensi.longitude_pulang = data["lng"]
        presensi.save()

        return Response({
            "diterima": True,
            "status": presensi.status,
            "waktu_pulang": presensi.waktu_pulang,
            "lokasi": hasil.lokasi.nama,
        })


class StatusHariIniView(APIView):
    """GET /api/presensi/status-hari-ini — status presensi dosen hari ini."""

    def get(self, request):
        nidn = request.user.nidn
        if not nidn:
            return Response({"diterima": False, "alasan": "nidn_tidak_terdaftar"}, status=status.HTTP_400_BAD_REQUEST)

        presensi = Presensi.objects.filter(nidn=nidn, tanggal=timezone.localdate()).first()
        if not presensi:
            return Response({"sudah_absen_masuk": False, "sudah_absen_pulang": False})

        return Response({
            "sudah_absen_masuk": presensi.waktu_masuk is not None,
            "sudah_absen_pulang": presensi.waktu_pulang is not None,
            "status": presensi.status,
            "waktu_masuk": presensi.waktu_masuk,
            "waktu_pulang": presensi.waktu_pulang,
        })
