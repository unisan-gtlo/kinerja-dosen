from django.urls import path

from . import views

app_name = "presensi"

urlpatterns = [
    path("masuk", views.AbsenMasukView.as_view(), name="masuk"),
    path("pulang", views.AbsenPulangView.as_view(), name="pulang"),
    path("status-hari-ini", views.StatusHariIniView.as_view(), name="status_hari_ini"),
    path("enrolment-wajah", views.EnrolmentWajahView.as_view(), name="enrolment_wajah"),
    path("paraf", views.ParafDosenView.as_view(), name="paraf"),
]
