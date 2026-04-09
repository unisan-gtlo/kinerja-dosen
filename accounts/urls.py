from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('kelola-user/', views.kelola_user, name='kelola_user'),
    path('tambah-user/', views.tambah_user, name='tambah_user'),
    path('edit-user/<int:user_id>/', views.edit_user, name='edit_user'),
    path('hapus-user/<int:user_id>/', views.hapus_user, name='hapus_user'),
]