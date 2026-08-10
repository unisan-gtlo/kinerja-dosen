"""Paksa ganti password sebelum bisa akses menu lain, kalau password
masih sama dengan bawaan (username sendiri atau default fallback import
Excel "unichsan123") -- lihat accounts/views.py::login_view (flag
dihitung SEKALI saat login, disimpan di sesi, bukan field database) dan
ganti_password (flag dihapus begitu password berhasil diganti)."""
EXEMPT_PATHS = [
    '/accounts/login/',
    '/accounts/logout/',
    '/accounts/ganti-password/',
    '/accounts/refresh-captcha/',
    '/admin/',
    '/static/',
    '/media/',
]


class WajibGantiPasswordMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and request.session.get('wajib_ganti_password')
            and not self._is_exempt(request.path)
        ):
            from django.shortcuts import redirect
            return redirect('accounts:ganti_password')
        return self.get_response(request)

    def _is_exempt(self, path):
        return any(path.startswith(exempt) for exempt in EXEMPT_PATHS)
