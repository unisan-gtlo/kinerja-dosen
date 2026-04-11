from django.contrib import admin
from django.urls import path, include
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    path('master/', include('master.urls')),
    path('profil/', include('profil.urls')),
    path('kinerja/', include('kinerja.urls')),
    path('laporan/', include('laporan.urls')),
]

# Protected media — hanya bisa diakses saat login
if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
else:
    from accounts.media_views import serve_protected_media
    from django.urls import re_path
    urlpatterns += [
        re_path(
            r'^media/(?P<path>.*)$',
            serve_protected_media,
            name='protected_media'
        ),
    ]