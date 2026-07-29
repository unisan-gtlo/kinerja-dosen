from django.urls import path

from . import views

app_name = "presensi_web"

urlpatterns = [
    path("", views.halaman_absen, name="index"),
    path("enrolment/", views.halaman_enrolment, name="enrolment"),
    path("dashboard/", views.dashboard_presensi, name="dashboard"),
    path("data/", views.data_presensi, name="data"),
    path("data/ekspor/", views.export_excel_presensi, name="data_ekspor"),
    path("tinjau/", views.tinjau_presensi, name="tinjau"),
    path("tinjau/<int:presensi_id>/putuskan/", views.putuskan_presensi, name="putuskan"),
    path("riwayat/", views.halaman_riwayat, name="riwayat"),
    path("izin/", views.halaman_izin, name="izin"),
    path("izin/tinjau/", views.tinjau_izin, name="izin_tinjau"),
    path("izin/tinjau/<int:izin_id>/putuskan/", views.putuskan_izin, name="izin_putuskan"),
    path("sw.js", views.service_worker_presensi, name="sw"),
]
