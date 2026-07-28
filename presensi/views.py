from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from accounts.models import User
from simda_dosen.utils import dapat_kelola_nidn
from .decision import cek_lokasi, tentukan_status_waktu
from .models import LogKecurangan, Perangkat, Presensi, StatusPresensi, TingkatRisiko
from .serializers import AbsenSerializer

# Sama seperti accounts/views.py::ROLE_PENGELOLA_SCOPED -- peran yang boleh
# mengelola dosen dalam cakupannya sendiri (fakultas/prodi), dipakai di sini
# untuk menentukan siapa yang boleh meninjau presensi ditandai.
ROLE_PENGELOLA_SCOPED = ("dekan", "wadek", "kaprodi", "sekprodi", "operator")


@login_required
def halaman_absen(request):
    """Halaman web untuk dosen absen masuk/pulang (Tabler UI + JS geolocation,
    memanggil API /api/presensi/masuk & /pulang lewat sesi Django yang sudah
    login -- lihat SessionAuthentication di REST_FRAMEWORK settings)."""
    return render(request, "presensi/absen.html")


def _bisa_tinjau_presensi(user):
    return user.role == "admin" or user.role in ROLE_PENGELOLA_SCOPED


@login_required
def tinjau_presensi(request):
    """Halaman HR/admin: daftar presensi yang ditandai (tingkat_risiko
    sedang/tinggi) untuk ditinjau manual -- lihat CLAUDE.md § 3. Dibatasi ke
    dosen dalam cakupan reviewer (fakultas/prodi), sama seperti pola
    dapat_kelola_nidn yang sudah dipakai app profil."""
    if not _bisa_tinjau_presensi(request.user):
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")

    semua_ditandai = Presensi.objects.filter(ditandai=True).select_related("lokasi").order_by("-tanggal", "nidn")
    antrian = [p for p in semua_ditandai if dapat_kelola_nidn(request.user, p.nidn)]

    nama_dosen = {
        u.nidn: u.get_full_name() or u.username
        for u in User.objects.filter(nidn__in=[p.nidn for p in antrian])
    }

    daftar = [{"presensi": p, "nama_dosen": nama_dosen.get(p.nidn, "—")} for p in antrian]

    return render(request, "presensi/tinjau.html", {"daftar": daftar})


@login_required
def putuskan_presensi(request, presensi_id):
    """POST-only: HR/admin menyetujui atau menolak satu presensi ditandai."""
    if not _bisa_tinjau_presensi(request.user):
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")
    if request.method != "POST":
        return redirect("presensi_web:tinjau")

    presensi = get_object_or_404(Presensi, id=presensi_id, ditandai=True)
    if not dapat_kelola_nidn(request.user, presensi.nidn):
        return HttpResponseForbidden("Anda tidak memiliki akses ke presensi dosen ini.")

    aksi = request.POST.get("aksi")
    if aksi == "setujui":
        presensi.ditandai = False
        presensi.tingkat_risiko = TingkatRisiko.RENDAH
        presensi.save(update_fields=["ditandai", "tingkat_risiko"])
        messages.success(request, f"Presensi {presensi.nidn} tanggal {presensi.tanggal} disetujui.")
    elif aksi == "tolak":
        presensi.status = StatusPresensi.DITOLAK
        presensi.ditandai = False
        presensi.save(update_fields=["status", "ditandai"])
        LogKecurangan.objects.create(
            nidn=presensi.nidn, presensi=presensi, jenis_anomali="ditolak_hr",
            skor=100, detail={"oleh": request.user.username},
        )
        messages.warning(request, f"Presensi {presensi.nidn} tanggal {presensi.tanggal} ditolak.")
    else:
        messages.error(request, "Aksi tidak dikenal.")

    return redirect("presensi_web:tinjau")


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
