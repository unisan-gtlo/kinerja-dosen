from django.urls import path
from . import views

app_name = 'penunjang'

urlpatterns = [
    path('', views.index, name='index'),

    path('tambah-profesi/', views.tambah_profesi, name='tambah_profesi'),
    path('edit-profesi/<int:id>/', views.edit_profesi, name='edit_profesi'),
    path('hapus-profesi/<int:id>/', views.hapus_profesi, name='hapus_profesi'),

    path('tambah-penghargaan/', views.tambah_penghargaan, name='tambah_penghargaan'),
    path('edit-penghargaan/<int:id>/', views.edit_penghargaan, name='edit_penghargaan'),
    path('hapus-penghargaan/<int:id>/', views.hapus_penghargaan, name='hapus_penghargaan'),

    path('tambah-penunjang/', views.tambah_penunjang, name='tambah_penunjang'),
    path('edit-penunjang/<int:id>/', views.edit_penunjang, name='edit_penunjang'),
    path('hapus-penunjang/<int:id>/', views.hapus_penunjang, name='hapus_penunjang'),
    path('kelola-anggota/<int:penunjang_id>/', views.kelola_anggota_penunjang, name='kelola_anggota_penunjang'),
]
