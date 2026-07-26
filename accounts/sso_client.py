import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

SSO_VERIFY_URL  = getattr(settings, 'SSO_VERIFY_URL', 'https://sso.unisan-g.id/api/verify-token/')
SSO_SECRET_KEY  = getattr(settings, 'SSO_SECRET_KEY', '')
SSO_COOKIE_NAME = getattr(settings, 'SSO_COOKIE_NAME', 'sso_token')
SSO_TIMEOUT     = getattr(settings, 'SSO_TIMEOUT', 5)


def verify_sso_token(token):
    if not token or not SSO_SECRET_KEY:
        return None, 'Konfigurasi SSO tidak lengkap'

    try:
        response = requests.post(
            SSO_VERIFY_URL,
            json={'token': token},
            headers={
                'Authorization': f'Bearer {SSO_SECRET_KEY}',
                'Content-Type': 'application/json',
            },
            timeout=SSO_TIMEOUT,
        )

        if response.status_code == 200:
            data = response.json()
            if data.get('valid'):
                return data.get('user'), None
            return None, data.get('error', 'Token tidak valid')

        elif response.status_code == 401:
            return None, 'Secret key SIKD tidak dikenal oleh SSO'

        elif response.status_code == 403:
            return None, 'Akun tidak memiliki akses ke SIKD'

        return None, f'SSO error: {response.status_code}'

    except requests.exceptions.Timeout:
        logger.warning('SSO verify timeout')
        return None, 'SSO tidak merespons'
    except requests.exceptions.ConnectionError:
        logger.warning('SSO tidak dapat dihubungi')
        return None, 'SSO tidak dapat dihubungi'
    except Exception as e:
        logger.error(f'SSO verify error: {e}')
        return None, 'SSO error tidak diketahui'


def get_sso_token_from_request(request):
    token = request.COOKIES.get(SSO_COOKIE_NAME, '')
    if not token:
        token = request.GET.get('sso_token', '')
    return token