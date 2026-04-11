from django.urls import path
from . import views

app_name = 'kinerja'

urlpatterns = [
    path('', views.index, name='index'),
    path('tambah-bkd/', views.tambah_bkd, name='tambah_bkd'),
    path('hapus-bkd/<int:bkd_id>/', views.hapus_bkd, name='hapus_bkd'),
    path('tambah-penelitian/', views.tambah_penelitian, name='tambah_penelitian'),
    path('hapus-penelitian/<int:id>/', views.hapus_penelitian, name='hapus_penelitian'),
    path('tambah-publikasi/', views.tambah_publikasi, name='tambah_publikasi'),
    path('hapus-publikasi/<int:id>/', views.hapus_publikasi, name='hapus_publikasi'),
    path('tambah-pkm/', views.tambah_pkm, name='tambah_pkm'),
    path('hapus-pkm/<int:id>/', views.hapus_pkm, name='hapus_pkm'),
    path('tambah-hki/', views.tambah_hki, name='tambah_hki'),
    path('hapus-hki/<int:id>/', views.hapus_hki, name='hapus_hki'),
    path('dokumen/<str:jenis_kinerja>/<int:kinerja_id>/', views.kelola_dokumen, name='kelola_dokumen'),
    path('edit-bkd/<int:id>/', views.edit_bkd, name='edit_bkd'),
    path('edit-penelitian/<int:id>/', views.edit_penelitian, name='edit_penelitian'),
    path('edit-publikasi/<int:id>/', views.edit_publikasi, name='edit_publikasi'),
    path('edit-pkm/<int:id>/', views.edit_pkm, name='edit_pkm'),
    path('edit-hki/<int:id>/', views.edit_hki, name='edit_hki'),
]