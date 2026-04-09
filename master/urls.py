from django.urls import path
from . import views

app_name = 'master'

urlpatterns = [
    path('', views.index, name='index'),
    path('simpan-fakultas/', views.simpan_fakultas, name='simpan_fakultas'),
    path('simpan-prodi/', views.simpan_prodi, name='simpan_prodi'),
    path('simpan-tahun/', views.simpan_tahun, name='simpan_tahun'),
    path('simpan-pengaturan/', views.simpan_pengaturan, name='simpan_pengaturan'),
]