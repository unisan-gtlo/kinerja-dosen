from django.urls import path

from . import views

app_name = "presensi_web"

urlpatterns = [
    path("", views.halaman_absen, name="index"),
]
