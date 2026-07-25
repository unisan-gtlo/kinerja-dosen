from django.contrib import admin
from .models import Beasiswa, Kesejahteraan, Tunjangan


@admin.register(Beasiswa)
class BeasiswaAdmin(admin.ModelAdmin):
    list_display = ['user', 'nama_beasiswa', 'jenis_beasiswa', 'tahun_mulai', 'masih_terima']
    list_filter = ['jenis_beasiswa', 'masih_terima']
    search_fields = ['user__username', 'nama_beasiswa']


@admin.register(Kesejahteraan)
class KesejahteraanAdmin(admin.ModelAdmin):
    list_display = ['user', 'layanan_kesejahteraan', 'jenis_kesejahteraan', 'penyelenggara', 'tahun_mulai']
    list_filter = ['jenis_kesejahteraan']
    search_fields = ['user__username', 'layanan_kesejahteraan']


@admin.register(Tunjangan)
class TunjanganAdmin(admin.ModelAdmin):
    list_display = ['user', 'nama_tunjangan', 'jenis_tunjangan', 'tahun_mulai', 'nominal']
    list_filter = ['jenis_tunjangan']
    search_fields = ['user__username', 'nama_tunjangan']
