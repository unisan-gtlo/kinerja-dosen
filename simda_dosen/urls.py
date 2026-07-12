from django.urls import path
from . import views

app_name = 'simda_dosen'

urlpatterns = [
    path('cari-mata-kuliah/', views.cari_mata_kuliah, name='cari_mata_kuliah'),
    path('cari-mahasiswa/', views.cari_mahasiswa, name='cari_mahasiswa'),
    path('cari-dosen/', views.cari_dosen, name='cari_dosen'),
]
