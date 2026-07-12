from django.urls import path
from . import views

app_name = 'penelitian'

urlpatterns = [
    path('', views.index, name='index'),

    path('tambah-penelitian/', views.tambah_penelitian, name='tambah_penelitian'),
    path('edit-penelitian/<int:id>/', views.edit_penelitian, name='edit_penelitian'),
    path('hapus-penelitian/<int:id>/', views.hapus_penelitian, name='hapus_penelitian'),
    path('kelola-anggota/<int:penelitian_id>/', views.kelola_anggota_penelitian, name='kelola_anggota_penelitian'),

    path('tambah-publikasi/', views.tambah_publikasi, name='tambah_publikasi'),
    path('edit-publikasi/<int:id>/', views.edit_publikasi, name='edit_publikasi'),
    path('hapus-publikasi/<int:id>/', views.hapus_publikasi, name='hapus_publikasi'),
    path('kelola-penulis-publikasi/<int:publikasi_id>/', views.kelola_penulis_publikasi, name='kelola_penulis_publikasi'),

    path('tambah-paten/', views.tambah_paten, name='tambah_paten'),
    path('edit-paten/<int:id>/', views.edit_paten, name='edit_paten'),
    path('hapus-paten/<int:id>/', views.hapus_paten, name='hapus_paten'),
    path('kelola-penulis-paten/<int:paten_id>/', views.kelola_penulis_paten, name='kelola_penulis_paten'),
]
