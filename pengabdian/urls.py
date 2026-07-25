from django.urls import path
from . import views

app_name = 'pengabdian'

urlpatterns = [
    path('', views.index, name='index'),

    path('tambah-pengabdian/', views.tambah_pengabdian, name='tambah_pengabdian'),
    path('edit-pengabdian/<int:id>/', views.edit_pengabdian, name='edit_pengabdian'),
    path('hapus-pengabdian/<int:id>/', views.hapus_pengabdian, name='hapus_pengabdian'),
    path('kelola-anggota/<int:pengabdian_id>/', views.kelola_anggota_pengabdian, name='kelola_anggota_pengabdian'),

    path('tambah-pembicara/', views.tambah_pembicara, name='tambah_pembicara'),
    path('edit-pembicara/<int:id>/', views.edit_pembicara, name='edit_pembicara'),
    path('hapus-pembicara/<int:id>/', views.hapus_pembicara, name='hapus_pembicara'),

    path('tambah-jurnal/', views.tambah_jurnal, name='tambah_jurnal'),
    path('edit-jurnal/<int:id>/', views.edit_jurnal, name='edit_jurnal'),
    path('hapus-jurnal/<int:id>/', views.hapus_jurnal, name='hapus_jurnal'),

    path('tambah-jabatan/', views.tambah_jabatan, name='tambah_jabatan'),
    path('edit-jabatan/<int:id>/', views.edit_jabatan, name='edit_jabatan'),
    path('hapus-jabatan/<int:id>/', views.hapus_jabatan, name='hapus_jabatan'),
]
