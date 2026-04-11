import os
from django.http import FileResponse, Http404
from django.contrib.auth.decorators import login_required
from django.conf import settings

@login_required
def serve_protected_media(request, path):
    """Serve media files hanya untuk user yang login"""
    file_path = os.path.join(settings.MEDIA_ROOT, path)

    if not os.path.exists(file_path):
        raise Http404

    # Cek akses — hanya admin atau pemilik file
    # Untuk simplisitas, cukup cek login
    return FileResponse(open(file_path, 'rb'))