import logging
from django.contrib.auth import login
from django.utils import timezone
from accounts.sso_client import verify_sso_token, get_sso_token_from_request
from accounts.models import User

logger = logging.getLogger(__name__)

EXEMPT_PATHS = [
    '/accounts/login/',
    '/accounts/logout/',
    '/admin/',
    '/static/',
    '/media/',
]


class SSOAutoLoginMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self._try_sso_login(request)
        response = self.get_response(request)
        return response

    def _try_sso_login(self, request):
        if self._is_exempt(request.path):
            return

        if request.user.is_authenticated:
            return

        token = get_sso_token_from_request(request)
        if not token:
            return

        sso_user_data, error = verify_sso_token(token)
        if error or not sso_user_data:
            logger.debug(f'SSO middleware skip: {error}')
            return

        username = sso_user_data.get('username')
        if not username:
            return

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = self._provision_user(sso_user_data)
            if not user:
                return
        except Exception as e:
            logger.error(f'SSO auto-login error: {e}')
            return

        if user.status_akun != 'aktif':
            logger.warning(f'SSO login ditolak, akun SIKD nonaktif: {username}')
            return

        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        logger.info(
            f'SSO auto-login SIKD: {username} '
            f'| ip: {self._get_ip(request)}'
        )

    def _provision_user(self, sso_user_data):
        """JIT (Just-In-Time) provisioning: kalau token SSO valid tapi
        user belum ada di SIKD sama sekali, buat akun lokal otomatis
        supaya tidak perlu dibuat manual dua kali (SSO lalu SIKD).

        CATATAN: field selain 'username' di bawah ini ditebak secara
        defensif (belum ada dokumentasi resmi payload SSO) -- role
        SENGAJA selalu 'dosen' (paling rendah risiko, tidak pernah
        auto-elevate ke kaprodi/dekan/admin dst). Field nidn/fakultas/
        prodi kemungkinan perlu dilengkapi manual lewat Kelola User
        kalau SSO tidak mengirim field itu. Password diset unusable --
        akun ini memang cuma dimaksudkan login lewat SSO, bukan form
        login lokal SIKD.
        """
        username = sso_user_data.get('username')
        try:
            user = User.objects.create(
                username=username,
                first_name=sso_user_data.get('first_name') or sso_user_data.get('nama') or username,
                last_name=sso_user_data.get('last_name', ''),
                email=sso_user_data.get('email', ''),
                nidn=sso_user_data.get('nidn', ''),
                role='dosen',
                status_akun='aktif',
            )
            user.set_unusable_password()
            user.save()
            logger.info(
                f'SSO JIT-provisioning: akun SIKD baru dibuat otomatis untuk '
                f'"{username}" (role default: dosen). Field fakultas/prodi/'
                f'NIDN mungkin perlu dilengkapi manual lewat Kelola User. '
                f'Field yang dikirim SSO: {list(sso_user_data.keys())}'
            )
            return user
        except Exception as e:
            logger.error(f'SSO JIT-provisioning gagal untuk "{username}": {e}')
            return None

    def _is_exempt(self, path):
        for exempt in EXEMPT_PATHS:
            if path.startswith(exempt):
                return True
        return False

    def _get_ip(self, request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')