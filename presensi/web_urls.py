from django.urls import path

from . import views

app_name = "presensi_web"

urlpatterns = [
    path("", views.halaman_absen, name="index"),
    path("enrolment/", views.halaman_enrolment, name="enrolment"),
    path("dashboard/", views.dashboard_presensi, name="dashboard"),
    path("data/", views.data_presensi, name="data"),
    path("data/ekspor/", views.export_excel_presensi, name="data_ekspor"),
    path("laporan-bulanan/", views.laporan_bulanan_presensi, name="laporan_bulanan"),
    path("laporan-bulanan/ekspor/", views.export_excel_laporan_bulanan, name="laporan_bulanan_ekspor"),
    path("tinjau/", views.tinjau_presensi, name="tinjau"),
    path("tinjau/<int:presensi_id>/putuskan/", views.putuskan_presensi, name="putuskan"),
    path("tinjau/<int:presensi_id>/putuskan-lembur/", views.putuskan_lembur, name="putuskan_lembur"),
    path("riwayat/", views.halaman_riwayat, name="riwayat"),
    path("izin/", views.halaman_izin, name="izin"),
    path("izin/tinjau/", views.tinjau_izin, name="izin_tinjau"),
    path("izin/tinjau/<int:izin_id>/putuskan/", views.putuskan_izin, name="izin_putuskan"),
    path("sw.js", views.service_worker_presensi, name="sw"),

    path("pengaturan/kelompok/", views.pengaturan_kelompok, name="pengaturan_kelompok"),
    path("pengaturan/kelompok/tambah/", views.tambah_kelompok, name="tambah_kelompok"),
    path("pengaturan/kelompok/<int:kelompok_id>/ubah/", views.ubah_kelompok, name="ubah_kelompok"),
    path(
        "pengaturan/kelompok/<int:kelompok_id>/toggle-aktif/", views.toggle_aktif_kelompok,
        name="toggle_aktif_kelompok",
    ),
    path("pengaturan/hari-libur/", views.pengaturan_hari_libur, name="pengaturan_hari_libur"),
    path("pengaturan/hari-libur/tambah/", views.tambah_hari_libur, name="tambah_hari_libur"),
    path("pengaturan/hari-libur/<int:hari_libur_id>/hapus/", views.hapus_hari_libur, name="hapus_hari_libur"),
    path("pengaturan/target/", views.pengaturan_target, name="pengaturan_target"),
    path("pengaturan/target/tambah/", views.tambah_target, name="tambah_target"),
    path("pengaturan/target/<int:target_id>/ubah/", views.ubah_target, name="ubah_target"),
    path("pengaturan/target/<int:target_id>/hapus/", views.hapus_target, name="hapus_target"),
]
