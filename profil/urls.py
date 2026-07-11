from django.urls import path
from . import views

app_name = 'profil'

urlpatterns = [
    path('', views.index, name='index'),
    path('simpan-profil/', views.simpan_profil, name='simpan_profil'),
    path('tambah-jabfung/', views.tambah_jabfung, name='tambah_jabfung'),
    path('edit-jabfung/<int:jabfung_id>/', views.edit_jabfung, name='edit_jabfung'),
    path('hapus-jabfung/<int:jabfung_id>/', views.hapus_jabfung, name='hapus_jabfung'),
    path('tambah-pendidikan/', views.tambah_pendidikan, name='tambah_pendidikan'),
    path('edit-pendidikan/<int:pend_id>/', views.edit_pendidikan, name='edit_pendidikan'),
    path('hapus-pendidikan/<int:pend_id>/', views.hapus_pendidikan, name='hapus_pendidikan'),
    path('kualifikasi/', views.kualifikasi_index, name='kualifikasi_index'),
    path('tambah-diklat/', views.tambah_diklat, name='tambah_diklat'),
    path('edit-diklat/<int:id>/', views.edit_diklat, name='edit_diklat'),
    path('hapus-diklat/<int:id>/', views.hapus_diklat, name='hapus_diklat'),
    path('kompetensi/', views.kompetensi_index, name='kompetensi_index'),
    path('tambah-sertifikasi/', views.tambah_sertifikasi, name='tambah_sertifikasi'),
    path('edit-sertifikasi/<int:id>/', views.edit_sertifikasi, name='edit_sertifikasi'),
    path('hapus-sertifikasi/<int:id>/', views.hapus_sertifikasi, name='hapus_sertifikasi'),
    path('tambah-tes/', views.tambah_tes, name='tambah_tes'),
    path('edit-tes/<int:id>/', views.edit_tes, name='edit_tes'),
    path('hapus-tes/<int:id>/', views.hapus_tes, name='hapus_tes'),
]