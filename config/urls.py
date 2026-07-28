from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    path('master/', include('master.urls')),
    path('profil/', include('profil.urls')),
    path('kinerja/', include('kinerja.urls')),
    path('pendidikan/', include('pendidikan.urls')),
    path('penelitian/', include('penelitian.urls')),
    path('pengabdian/', include('pengabdian.urls')),
    path('penunjang/', include('penunjang.urls')),
    path('reward/', include('reward.urls')),
    path('laporan/', include('laporan.urls')),
    path('simda-dosen/', include('simda_dosen.urls')),
    # Halaman web presensi (absen masuk/pulang lewat browser).
    path('presensi/', include('presensi.web_urls')),
    # API modul presensi (JWT, dipakai klien mobile/PWA -- lihat
    # docs/presensi/spesifikasiapipresensi.md).
    path('api/auth/login', TokenObtainPairView.as_view(), name='api_login'),
    path('api/auth/refresh', TokenRefreshView.as_view(), name='api_refresh'),
    path('api/presensi/', include('presensi.urls')),
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