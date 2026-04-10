from django.urls import path
from . import views

app_name = 'laporan'

urlpatterns = [
    path('', views.index, name='index'),
    path('excel/rekap/', views.export_excel_rekap, name='excel_rekap'),
    path('excel/penelitian/', views.export_excel_penelitian, name='excel_penelitian'),
    path('excel/publikasi/', views.export_excel_publikasi, name='excel_publikasi'),
    path('pdf/rekap/', views.export_pdf_rekap, name='pdf_rekap'),
]