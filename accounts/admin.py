from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'get_full_name', 'role', 'kode_fakultas', 'kode_prodi', 'status_akun']
    list_filter = ['role', 'kode_fakultas', 'status_akun']
    search_fields = ['username', 'first_name', 'last_name', 'nidn']
    fieldsets = UserAdmin.fieldsets + (
        ('Data SIKD', {
            'fields': ('role', 'nidn', 'nip_yayasan', 'kode_fakultas', 'kode_prodi', 'no_hp', 'status_akun')
        }),
    )