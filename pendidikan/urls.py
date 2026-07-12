from django.urls import path
from . import views

app_name = 'pendidikan'

urlpatterns = [
    path('', views.index, name='index'),

    path('tambah-pengajaran/', views.tambah_pengajaran, name='tambah_pengajaran'),
    path('edit-pengajaran/<int:id>/', views.edit_pengajaran, name='edit_pengajaran'),
    path('hapus-pengajaran/<int:id>/', views.hapus_pengajaran, name='hapus_pengajaran'),

    path('tambah-bimbingan/', views.tambah_bimbingan, name='tambah_bimbingan'),
    path('edit-bimbingan/<int:id>/', views.edit_bimbingan, name='edit_bimbingan'),
    path('hapus-bimbingan/<int:id>/', views.hapus_bimbingan, name='hapus_bimbingan'),

    path('tambah-pengujian/', views.tambah_pengujian, name='tambah_pengujian'),
    path('edit-pengujian/<int:id>/', views.edit_pengujian, name='edit_pengujian'),
    path('hapus-pengujian/<int:id>/', views.hapus_pengujian, name='hapus_pengujian'),

    path('tambah-bahan-ajar/', views.tambah_bahan_ajar, name='tambah_bahan_ajar'),
    path('edit-bahan-ajar/<int:id>/', views.edit_bahan_ajar, name='edit_bahan_ajar'),
    path('hapus-bahan-ajar/<int:id>/', views.hapus_bahan_ajar, name='hapus_bahan_ajar'),

    path('tambah-pembinaan-mahasiswa/', views.tambah_pembinaan_mahasiswa, name='tambah_pembinaan_mahasiswa'),
    path('edit-pembinaan-mahasiswa/<int:id>/', views.edit_pembinaan_mahasiswa, name='edit_pembinaan_mahasiswa'),
    path('hapus-pembinaan-mahasiswa/<int:id>/', views.hapus_pembinaan_mahasiswa, name='hapus_pembinaan_mahasiswa'),

    path('tambah-orasi-ilmiah/', views.tambah_orasi_ilmiah, name='tambah_orasi_ilmiah'),
    path('edit-orasi-ilmiah/<int:id>/', views.edit_orasi_ilmiah, name='edit_orasi_ilmiah'),
    path('hapus-orasi-ilmiah/<int:id>/', views.hapus_orasi_ilmiah, name='hapus_orasi_ilmiah'),

    path('tambah-tugas-tambahan/', views.tambah_tugas_tambahan, name='tambah_tugas_tambahan'),
    path('edit-tugas-tambahan/<int:id>/', views.edit_tugas_tambahan, name='edit_tugas_tambahan'),
    path('hapus-tugas-tambahan/<int:id>/', views.hapus_tugas_tambahan, name='hapus_tugas_tambahan'),
]
