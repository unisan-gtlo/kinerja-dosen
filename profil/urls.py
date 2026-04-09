from django.urls import path
from . import views

app_name = 'profil'

urlpatterns = [
    path('', views.index, name='index'),
    path('simpan-profil/', views.simpan_profil, name='simpan_profil'),
    path('tambah-jabfung/', views.tambah_jabfung, name='tambah_jabfung'),
    path('hapus-jabfung/<int:jabfung_id>/', views.hapus_jabfung, name='hapus_jabfung'),
    path('tambah-pendidikan/', views.tambah_pendidikan, name='tambah_pendidikan'),
    path('hapus-pendidikan/<int:pend_id>/', views.hapus_pendidikan, name='hapus_pendidikan'),
    path('tambah-sertifikat/', views.tambah_sertifikat, name='tambah_sertifikat'),
    path('hapus-sertifikat/<int:sert_id>/', views.hapus_sertifikat, name='hapus_sertifikat'),
]