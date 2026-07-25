from django.urls import path
from . import views

app_name = 'reward'

urlpatterns = [
    path('', views.index, name='index'),

    path('tambah-beasiswa/', views.tambah_beasiswa, name='tambah_beasiswa'),
    path('edit-beasiswa/<int:id>/', views.edit_beasiswa, name='edit_beasiswa'),
    path('hapus-beasiswa/<int:id>/', views.hapus_beasiswa, name='hapus_beasiswa'),

    path('tambah-kesejahteraan/', views.tambah_kesejahteraan, name='tambah_kesejahteraan'),
    path('edit-kesejahteraan/<int:id>/', views.edit_kesejahteraan, name='edit_kesejahteraan'),
    path('hapus-kesejahteraan/<int:id>/', views.hapus_kesejahteraan, name='hapus_kesejahteraan'),

    path('tambah-tunjangan/', views.tambah_tunjangan, name='tambah_tunjangan'),
    path('edit-tunjangan/<int:id>/', views.edit_tunjangan, name='edit_tunjangan'),
    path('hapus-tunjangan/<int:id>/', views.hapus_tunjangan, name='hapus_tunjangan'),
]
