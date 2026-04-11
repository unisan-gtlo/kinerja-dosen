from django.urls import path
from . import views

app_name = 'laporan'

urlpatterns = [
    path('', views.index, name='index'),
    path('excel/rekap/', views.export_excel_rekap, name='excel_rekap'),
    path('excel/penelitian/', views.export_excel_penelitian, name='excel_penelitian'),
    path('excel/publikasi/', views.export_excel_publikasi, name='excel_publikasi'),
    path('excel/pkm/', views.export_excel_pkm, name='excel_pkm'),
    path('excel/hki/', views.export_excel_hki, name='excel_hki'),
    path('excel/statistik-kinerja/', views.export_excel_statistik_kinerja, name='excel_statistik_kinerja'),
    path('excel/statistik-profil/', views.export_excel_statistik_profil, name='excel_statistik_profil'),
    path('pdf/rekap/', views.export_pdf_rekap, name='pdf_rekap'),
    path('pdf/dosen/<int:dosen_id>/', views.export_pdf_dosen, name='pdf_dosen'),
]