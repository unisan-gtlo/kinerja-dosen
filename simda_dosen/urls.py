from django.urls import path
from . import views

app_name = 'simda_dosen'

urlpatterns = [
    path('cari-mata-kuliah/', views.cari_mata_kuliah, name='cari_mata_kuliah'),
    path('cari-mahasiswa/', views.cari_mahasiswa, name='cari_mahasiswa'),
    path('cari-dosen/', views.cari_dosen, name='cari_dosen'),

    path('tendik/', views.daftar_tendik, name='daftar_tendik'),
    path('tendik/ekspor/pdf/', views.export_pdf_daftar_tendik, name='export_pdf_daftar_tendik'),
    path('tendik/ekspor/excel/', views.export_excel_daftar_tendik, name='export_excel_daftar_tendik'),
    path('tendik/tambah/', views.tambah_tendik, name='tambah_tendik'),
    path('tendik/<int:tendik_id>/ubah/', views.ubah_tendik, name='ubah_tendik'),
    path('tendik/<int:tendik_id>/toggle-aktif/', views.toggle_aktif_tendik, name='toggle_aktif_tendik'),
    path('tendik/<int:tendik_id>/detail/', views.detail_tendik, name='detail_tendik'),
    path('profil-riwayat-saya/', views.profil_riwayat_saya, name='profil_riwayat_saya'),
    path('profil-riwayat-saya/simpan/', views.simpan_profil_saya_tendik, name='simpan_profil_saya_tendik'),

    path('tendik/<int:tendik_id>/riwayat-pendidikan/tambah/',
         views.tambah_riwayat_pendidikan_tendik, name='tambah_riwayat_pendidikan_tendik'),
    path('tendik/riwayat-pendidikan/<int:riwayat_id>/ubah/',
         views.edit_riwayat_pendidikan_tendik, name='edit_riwayat_pendidikan_tendik'),
    path('tendik/riwayat-pendidikan/<int:riwayat_id>/hapus/',
         views.hapus_riwayat_pendidikan_tendik, name='hapus_riwayat_pendidikan_tendik'),

    path('tendik/<int:tendik_id>/riwayat-pelatihan/tambah/',
         views.tambah_riwayat_pelatihan_tendik, name='tambah_riwayat_pelatihan_tendik'),
    path('tendik/riwayat-pelatihan/<int:riwayat_id>/ubah/',
         views.edit_riwayat_pelatihan_tendik, name='edit_riwayat_pelatihan_tendik'),
    path('tendik/riwayat-pelatihan/<int:riwayat_id>/hapus/',
         views.hapus_riwayat_pelatihan_tendik, name='hapus_riwayat_pelatihan_tendik'),

    path('tendik/<int:tendik_id>/riwayat-prestasi/tambah/',
         views.tambah_riwayat_prestasi_tendik, name='tambah_riwayat_prestasi_tendik'),
    path('tendik/riwayat-prestasi/<int:riwayat_id>/ubah/',
         views.edit_riwayat_prestasi_tendik, name='edit_riwayat_prestasi_tendik'),
    path('tendik/riwayat-prestasi/<int:riwayat_id>/hapus/',
         views.hapus_riwayat_prestasi_tendik, name='hapus_riwayat_prestasi_tendik'),
]
