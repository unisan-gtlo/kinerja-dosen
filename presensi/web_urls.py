from django.urls import path

from . import views

app_name = "presensi_web"

urlpatterns = [
    path("", views.halaman_absen, name="index"),
    path("enrolment/", views.halaman_enrolment, name="enrolment"),
    path("tinjau/", views.tinjau_presensi, name="tinjau"),
    path("tinjau/<int:presensi_id>/putuskan/", views.putuskan_presensi, name="putuskan"),
    path("sw.js", views.service_worker_presensi, name="sw"),
]
