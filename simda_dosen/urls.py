from django.urls import path
from . import views

app_name = 'simda_dosen'

urlpatterns = [
    path('cari-mata-kuliah/', views.cari_mata_kuliah, name='cari_mata_kuliah'),
    path('cari-mahasiswa/', views.cari_mahasiswa, name='cari_mahasiswa'),
    path('cari-dosen/', views.cari_dosen, name='cari_dosen'),

    path('tendik/', views.daftar_tendik, name='daftar_tendik'),
    path('tendik/tambah/', views.tambah_tendik, name='tambah_tendik'),
    path('tendik/<int:tendik_id>/ubah/', views.ubah_tendik, name='ubah_tendik'),
    path('tendik/<int:tendik_id>/toggle-aktif/', views.toggle_aktif_tendik, name='toggle_aktif_tendik'),
]
