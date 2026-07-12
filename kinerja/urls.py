from django.urls import path
from . import views

app_name = 'kinerja'

urlpatterns = [
    path('', views.index, name='index'),
    path('bkd/', views.bkd_index, name='bkd_index'),
    path('tambah-bkd/', views.tambah_bkd, name='tambah_bkd'),
    path('hapus-bkd/<int:bkd_id>/', views.hapus_bkd, name='hapus_bkd'),
    path('tambah-pkm/', views.tambah_pkm, name='tambah_pkm'),
    path('hapus-pkm/<int:id>/', views.hapus_pkm, name='hapus_pkm'),
    path('dokumen/<str:jenis_kinerja>/<int:kinerja_id>/', views.kelola_dokumen, name='kelola_dokumen'),
    path('edit-bkd/<int:id>/', views.edit_bkd, name='edit_bkd'),
    path('edit-pkm/<int:id>/', views.edit_pkm, name='edit_pkm'),
    path('tambah-penghargaan/', views.tambah_penghargaan, name='tambah_penghargaan'),
    path('hapus-penghargaan/<int:id>/', views.hapus_penghargaan, name='hapus_penghargaan'),
    path('edit-penghargaan/<int:id>/', views.edit_penghargaan, name='edit_penghargaan'),
    path('tambah-penunjang/', views.tambah_penunjang, name='tambah_penunjang'),
    path('hapus-penunjang/<int:id>/', views.hapus_penunjang, name='hapus_penunjang'),
    path('edit-penunjang/<int:id>/', views.edit_penunjang, name='edit_penunjang'),
]
