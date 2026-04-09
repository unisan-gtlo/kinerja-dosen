from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    path('master/', include('master.urls')),
    path('profil/', include('profil.urls')),
    path('kinerja/', include('kinerja.urls')),
    path('laporan/', include('laporan.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)