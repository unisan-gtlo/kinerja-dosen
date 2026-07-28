from datetime import datetime

import openpyxl
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from accounts.models import User
from laporan.views import get_dosen_queryset
from simda_dosen.utils import dapat_kelola_nidn
from .decision import cek_lokasi, tentukan_status_waktu, verifikasi_wajah
from .face import VERSI_MODEL_WAJAH, ekstrak_satu_wajah, enkripsi_embedding, rata_rata_embedding
from .models import EnrolmentWajah, LogKecurangan, Perangkat, Presensi, StatusPresensi, TingkatRisiko
from .rekap import data_presensi_harian, ringkasan_hari_ini, top_telat_hari_ini, tren_mingguan
from .serializers import AbsenSerializer, EnrolmentWajahSerializer

# Sama seperti accounts/views.py::ROLE_PENGELOLA_SCOPED -- peran yang boleh
# mengelola dosen dalam cakupannya sendiri (fakultas/prodi), dipakai di sini
# untuk menentukan siapa yang boleh meninjau presensi ditandai.
ROLE_PENGELOLA_SCOPED = ("dekan", "wadek", "kaprodi", "sekprodi", "operator")


@login_required
def halaman_absen(request):
    """Halaman web untuk dosen absen masuk/pulang (Tabler UI + JS geolocation,
    memanggil API /api/presensi/masuk & /pulang lewat sesi Django yang sudah
    login -- lihat SessionAuthentication di REST_FRAMEWORK settings)."""
    sudah_enrolment = EnrolmentWajah.objects.filter(
        nidn=request.user.nidn, consent_disetujui=True,
    ).exists() if request.user.nidn else False
    return render(request, "presensi/absen.html", {"sudah_enrolment": sudah_enrolment})


@login_required
def halaman_enrolment(request):
    """Halaman web pendaftaran wajah (sekali di awal) -- ambil 2-5 selfie
    lewat kamera browser + persetujuan (consent), kirim ke
    /api/presensi/enrolment-wajah lewat sesi Django yang sudah login."""
    return render(request, "presensi/enrolment.html")


# Service worker minimal, sengaja TANPA caching berat -- halaman presensi
# butuh GPS/kamera live saat itu juga, jadi presensi offline tidak masuk
# akal. Isinya cuma cukup supaya browser menganggap /presensi/ "installable"
# (PWA Add to Home Screen).
_SERVICE_WORKER_JS = """
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', () => {});
""".strip()


def service_worker_presensi(request):
    """Sengaja disajikan lewat view (BUKAN file statis WhiteNoise): service
    worker cuma boleh mengontrol path yang sama atau di bawah lokasi
    skripnya sendiri, kecuali server mengirim header Service-Worker-Allowed.
    Dengan disajikan di /presensi/sw.js, cakupannya otomatis mencakup
    seluruh /presensi/ tanpa perlu konfigurasi header tambahan di Nginx."""
    return HttpResponse(_SERVICE_WORKER_JS, content_type="application/javascript")


def _bisa_tinjau_presensi(user):
    return user.role == "admin" or user.role in ROLE_PENGELOLA_SCOPED


def _tanggal_dari_request(request):
    tanggal_str = request.GET.get("tanggal")
    if tanggal_str:
        try:
            return datetime.strptime(tanggal_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    return timezone.localdate()


@login_required
def dashboard_presensi(request):
    """Dashboard admin/HR: KPI hari ini, tren 6 hari, dan daftar paling
    telat. Cakupan DOSEN SAJA untuk sekarang -- lihat catatan di
    presensi/rekap.py soal staf yang belum tercakup."""
    if not _bisa_tinjau_presensi(request.user):
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")

    dosen_qs = get_dosen_queryset(request.user)
    nidn_list = list(dosen_qs.exclude(nidn__isnull=True).exclude(nidn="").values_list("nidn", flat=True))

    ringkasan = ringkasan_hari_ini(nidn_list)
    tren = tren_mingguan(nidn_list)
    top_telat = top_telat_hari_ini(nidn_list)

    return render(request, "presensi/dashboard.html", {
        "ringkasan": ringkasan,
        "tren_labels": [t["label"] for t in tren],
        "tren_data": [t["jumlah"] for t in tren],
        "top_telat": top_telat,
    })


@login_required
def data_presensi(request):
    """Tabel data presensi harian (1 baris per dosen dalam cakupan,
    termasuk yang belum absen), dengan filter tanggal/fakultas/prodi."""
    if not _bisa_tinjau_presensi(request.user):
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")

    tanggal = _tanggal_dari_request(request)
    filter_fakultas = request.GET.get("fakultas", "")
    filter_prodi = request.GET.get("prodi", "")

    dosen_qs = get_dosen_queryset(request.user, filter_prodi=filter_prodi, filter_fakultas=filter_fakultas)
    daftar = data_presensi_harian(dosen_qs, tanggal)

    halaman = Paginator(daftar, 25).get_page(request.GET.get("halaman"))

    return render(request, "presensi/data.html", {
        "halaman": halaman,
        "tanggal": tanggal,
        "filter_fakultas": filter_fakultas,
        "filter_prodi": filter_prodi,
    })


@login_required
def export_excel_presensi(request):
    """Ekspor Excel data presensi harian -- style & pola sama dengan
    laporan/views.py supaya konsisten dengan ekspor lain di portal ini."""
    if not _bisa_tinjau_presensi(request.user):
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")

    tanggal = _tanggal_dari_request(request)
    filter_fakultas = request.GET.get("fakultas", "")
    filter_prodi = request.GET.get("prodi", "")

    dosen_qs = get_dosen_queryset(request.user, filter_prodi=filter_prodi, filter_fakultas=filter_fakultas)
    daftar = data_presensi_harian(dosen_qs, tanggal)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data Presensi"

    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="1e3a5f", end_color="1e3a5f", fill_type="solid")
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left = Alignment(horizontal="left", vertical="center", wrap_text=True)
    thin = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )

    ws.merge_cells("A1:H1")
    ws["A1"] = "DATA PRESENSI HARIAN"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A1"].alignment = center

    ws.merge_cells("A2:H2")
    ws["A2"] = f"Universitas Ichsan Gorontalo · {tanggal.strftime('%d %B %Y')}"
    ws["A2"].font = Font(bold=True, size=12)
    ws["A2"].alignment = center

    headers = ["No", "Nama", "NIDN", "Fakultas", "Prodi", "Masuk", "Pulang", "Status"]
    row_header = 4
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row_header, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center
        cell.border = thin
    ws.row_dimensions[row_header].height = 26

    for idx, item in enumerate(daftar, 1):
        dosen = item["dosen"]
        p = item["presensi"]
        row_data = [
            idx,
            dosen.get_full_name() or dosen.username,
            dosen.nidn,
            dosen.kode_fakultas or "-",
            dosen.kode_prodi or "-",
            timezone.localtime(p.waktu_masuk).strftime("%H:%M") if p and p.waktu_masuk else "-",
            timezone.localtime(p.waktu_pulang).strftime("%H:%M") if p and p.waktu_pulang else "-",
            p.get_status_display() if p else "Belum Absen",
        ]
        row_num = row_header + idx
        for col, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_num, column=col, value=value)
            cell.border = thin
            cell.alignment = center if col != 2 else left

    col_widths = [5, 28, 15, 10, 8, 10, 10, 14]
    for col, width in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(col)].width = width

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="Presensi_{tanggal.isoformat()}.xlsx"'
    wb.save(response)
    return response


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


# Skor risiko presensi yang lolos KEDUA syarat (lokasi & wajah) -- rendah
# tapi tidak nol, sisakan ruang untuk sinyal tambahan (QR/Wi-Fi) nanti.
SKOR_RISIKO_TERVERIFIKASI = 8

# Skor risiko dicatat ke LogKecurangan per jenis alasan gagal. Alasan yang
# TIDAK ada di sini (mis. "belum_enrolment_wajah", "foto_tidak_valid") sengaja
# tidak dicatat sebagai kecurangan -- itu soal kesiapan data, bukan indikasi
# curang.
SKOR_ANOMALI = {
    "akurasi_buruk": 60,
    "di_luar_radius": 70,
    "liveness_gagal": 75,
    "wajah_tidak_cocok": 90,
}


class PresensiRateThrottle(UserRateThrottle):
    scope = "presensi"


def _catat_perangkat(nidn, device_id, waktu):
    Perangkat.objects.update_or_create(
        nidn=nidn, device_id=device_id,
        defaults={"terakhir_dipakai": waktu},
    )


def _catat_jika_anomali(nidn, presensi, alasan, detail):
    if alasan in SKOR_ANOMALI:
        LogKecurangan.objects.create(
            nidn=nidn, presensi=presensi, jenis_anomali=alasan,
            skor=SKOR_ANOMALI[alasan], detail=detail,
        )


def _respon_ditolak(alasan):
    return Response({"diterima": False, "alasan": alasan, "tingkat_risiko": TingkatRisiko.TINGGI})


def _jalankan_gerbang(nidn, data, presensi=None):
    """Gerbang-DAN: cek_lokasi lalu (kalau lolos) verifikasi_wajah. Return
    (hasil_lokasi, None) kalau dua-duanya lolos, atau (None, Response) kalau
    salah satu gagal -- lihat presensi/decision.py."""
    hasil_lokasi = cek_lokasi(data["lat"], data["lng"], data["akurasi_m"])
    if not hasil_lokasi.lolos:
        _catat_jika_anomali(
            nidn, presensi, hasil_lokasi.alasan,
            {"lat": data["lat"], "lng": data["lng"], "akurasi_m": data["akurasi_m"]},
        )
        return None, _respon_ditolak(hasil_lokasi.alasan)

    hasil_wajah = verifikasi_wajah(nidn, data["selfie"])
    if not hasil_wajah.lolos:
        _catat_jika_anomali(nidn, presensi, hasil_wajah.alasan, {"skor_kemiripan": hasil_wajah.skor_kemiripan})
        return None, _respon_ditolak(hasil_wajah.alasan)

    return hasil_lokasi, None


class AbsenMasukView(APIView):
    """POST /api/presensi/masuk — absen masuk, gerbang-DAN cek lokasi + wajah."""
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

        hasil_lokasi, response_gagal = _jalankan_gerbang(nidn, data)
        if response_gagal is not None:
            return response_gagal

        status_kehadiran = tentukan_status_waktu(hasil_lokasi.lokasi, waktu_server.time())

        presensi, _ = Presensi.objects.update_or_create(
            nidn=nidn, tanggal=tanggal,
            defaults={
                "waktu_masuk": waktu_server,
                "lokasi": hasil_lokasi.lokasi,
                "latitude_masuk": data["lat"],
                "longitude_masuk": data["lng"],
                "akurasi_masuk_m": data["akurasi_m"],
                "status": status_kehadiran,
                "skor_risiko": SKOR_RISIKO_TERVERIFIKASI,
                "tingkat_risiko": TingkatRisiko.RENDAH,
                "ditandai": False,
            },
        )

        return Response({
            "diterima": True,
            "status": presensi.status,
            "waktu_masuk": presensi.waktu_masuk,
            "lokasi": hasil_lokasi.lokasi.nama,
            "skor_risiko": presensi.skor_risiko,
            "tingkat_risiko": presensi.tingkat_risiko,
        })


class AbsenPulangView(APIView):
    """POST /api/presensi/pulang — absen pulang, gerbang-DAN cek lokasi + wajah."""
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

        hasil_lokasi, response_gagal = _jalankan_gerbang(nidn, data, presensi=presensi)
        if response_gagal is not None:
            return response_gagal

        presensi.waktu_pulang = waktu_server
        presensi.lokasi = presensi.lokasi or hasil_lokasi.lokasi
        presensi.latitude_pulang = data["lat"]
        presensi.longitude_pulang = data["lng"]
        presensi.save()

        return Response({
            "diterima": True,
            "status": presensi.status,
            "waktu_pulang": presensi.waktu_pulang,
            "lokasi": hasil_lokasi.lokasi.nama,
        })


class EnrolmentWajahView(APIView):
    """POST /api/presensi/enrolment-wajah — daftarkan wajah dosen (sekali di
    awal, sebelum bisa lolos syarat 2 saat absen)."""
    throttle_classes = [PresensiRateThrottle]

    def post(self, request):
        serializer = EnrolmentWajahSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        nidn = request.user.nidn
        if not nidn:
            return Response(
                {"status": "gagal", "alasan": "nidn_tidak_terdaftar"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        embeddings = []
        for foto in data["foto"]:
            wajah, _alasan = ekstrak_satu_wajah(foto)
            if wajah is not None:
                embeddings.append(wajah.embedding)

        if len(embeddings) < 2:
            return Response(
                {"status": "gagal", "alasan": "wajah_tidak_terdeteksi_konsisten"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        embedding_rata = rata_rata_embedding(embeddings)
        waktu = timezone.now()

        EnrolmentWajah.objects.update_or_create(
            nidn=nidn,
            defaults={
                "embedding_terenkripsi": enkripsi_embedding(embedding_rata),
                "versi_model": VERSI_MODEL_WAJAH,
                "consent_disetujui": True,
                "consent_pada": waktu,
            },
        )

        return Response({"status": "ok", "versi_model": VERSI_MODEL_WAJAH, "consent_pada": waktu})


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
