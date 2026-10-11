"""
Pemeriksa akses file /media/ SIKD untuk nginx `auth_request`.

nginx memanggil /media-akses/ (subrequest internal, membawa cookie sesi dan header
X-Original-URI) sebelum melayani file dari /var/www/sikd/media/.
Jawaban 204 = boleh, 401 = belum login, 403 = tidak berhak.

Aturan (mengikuti User.can_view_all & User.dapat_kelola):
- Foto profil/dosen: semua pengguna yang login.
- Berkas milik seorang dosen (dokumen kinerja, dokumen profil, BKD, sertifikat,
  presensi: paraf/selfie/izin): pemiliknya, admin/rektorat/biro, dan atasan yang
  berhak mengelola dosen itu (dekan/wadek/operator se-fakultas, kaprodi/sekprodi se-prodi).
- Berkas lama tanpa pemilik yang bisa dikenali (mis. media/dosen/ktp/...): admin/rektorat/biro.
"""
import os
from urllib.parse import unquote, urlsplit

from django.http import HttpResponse

# Awalan path yang segmen berikutnya adalah username pemilik
AWALAN_PEMILIK = ('kinerja/dokumen/', 'dokumen/', 'profil/', 'bkd/', 'pendidikan/', 'sertifikat/', 'jabfung/')
FOTO = ('dosen/foto/',)


def _path_relatif(request):
    uri = request.META.get('HTTP_X_ORIGINAL_URI', '')
    path = unquote(urlsplit(uri).path)
    if not path.startswith('/media/'):
        return None
    rel = path[len('/media/'):]
    if not rel or rel.startswith('/') or '..' in rel.split('/'):
        return None
    return rel


def _pemilik(rel):
    """User pemilik berkas, atau None bila tidak bisa dikenali."""
    from accounts.models import User

    for awal in AWALAN_PEMILIK:
        if rel.startswith(awal):
            sisa = rel[len(awal):].split('/', 1)
            if len(sisa) == 2 and sisa[0]:
                return User.objects.filter(username=sisa[0]).first()
            return None
    if rel.startswith('presensi/'):
        from presensi.models import FotoPresensi, IzinCuti, ParafDosen
        for kueri in (ParafDosen.objects.filter(gambar=rel).values_list('user_id', flat=True),
                      IzinCuti.objects.filter(lampiran=rel).values_list('user_id', flat=True),
                      FotoPresensi.objects.filter(berkas=rel).values_list('presensi__user_id', flat=True)):
            uid = kueri.first()
            if uid:
                return User.objects.filter(pk=uid).first()
    return None


def media_akses(request):
    rel = _path_relatif(request)
    if rel is None:
        return HttpResponse(status=403)
    user = request.user
    if not user.is_authenticated:
        return HttpResponse(status=401)
    if getattr(user, 'status_akun', 'aktif') != 'aktif':
        return HttpResponse(status=403)
    if user.is_superuser or getattr(user, 'can_view_all', False):
        return HttpResponse(status=204)
    if rel.startswith(FOTO) or (rel.startswith('profil/') and os.path.basename(rel).lower().startswith('foto')):
        return HttpResponse(status=204)
    pemilik = _pemilik(rel)
    if pemilik is not None and user.dapat_kelola(pemilik):
        return HttpResponse(status=204)
    return HttpResponse(status=403)
