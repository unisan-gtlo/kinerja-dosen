from django.urls import path
from . import views

app_name = 'kinerja'

urlpatterns = [
    path('bkd/', views.bkd_index, name='bkd_index'),
    path('tambah-bkd/', views.tambah_bkd, name='tambah_bkd'),
    path('hapus-bkd/<int:bkd_id>/', views.hapus_bkd, name='hapus_bkd'),
    path('dokumen/<str:jenis_kinerja>/<int:kinerja_id>/', views.kelola_dokumen, name='kelola_dokumen'),
    path('edit-bkd/<int:id>/', views.edit_bkd, name='edit_bkd'),
]
