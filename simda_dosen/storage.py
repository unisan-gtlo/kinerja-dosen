from django.conf import settings
from django.core.files.storage import FileSystemStorage

# File dokumen dosen (KTP, foto, ijazah, SK, dst) harus fisik tersimpan di
# server SIMDA, bukan MEDIA_ROOT lokal SIKD -- karena baris datanya sama
# persis dengan tabel SIMDA (models.py di app ini managed=False, mirror
# tabel master.*). base_url mengarah langsung ke domain SIMDA supaya link
# dokumen tetap bisa dibuka dari SIKD walau file-nya fisik di server lain.
simda_media_storage = FileSystemStorage(
    location=settings.SIMDA_MEDIA_ROOT,
    base_url=settings.SIMDA_MEDIA_URL,
)
