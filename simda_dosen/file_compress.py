"""Kompresi otomatis file upload (gambar JPG/PNG & PDF) sebelum disimpan,
supaya ukurannya turun ke target (default ~480KB) tanpa perlu tool
tambahan di server (murni Pillow untuk gambar, PyMuPDF untuk PDF).

Dipakai di titik-titik upload dokumen (foto, KTP, NPWP, SK, Ijazah, dst)
di seluruh app -- lihat pemanggilan compress_uploaded_file() di
profil/views.py dan kinerja/views.py.

CATATAN untuk PDF: hasil kompresi me-render ulang tiap halaman jadi
gambar JPEG lalu menyusunnya kembali jadi PDF baru (rasterize). Untuk
dokumen hasil scan (KTP/SK/Ijazah -- kasus paling umum di aplikasi ini)
ini tidak masalah karena isinya memang sudah berupa gambar. Untuk PDF
yang aslinya dibuat digital (teks bisa di-select/di-copy), teks itu
akan hilang jadi bagian dari gambar setelah dikompres -- tidak ada cara
menghindari ini tanpa Ghostscript di server.
"""
import io
import logging

from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png'}
PDF_EXTENSIONS = {'pdf'}


def _get_extension(name):
    name = name or ''
    return name.rsplit('.', 1)[-1].lower() if '.' in name else ''


def _compress_image_bytes(data, max_bytes, min_quality=20, min_dimension=480):
    from PIL import Image

    img = Image.open(io.BytesIO(data))
    if img.mode in ('RGBA', 'P', 'LA'):
        img = img.convert('RGB')

    quality = 85
    while True:
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=quality, optimize=True)
        if buf.tell() <= max_bytes:
            return buf.getvalue()

        if quality > min_quality:
            quality -= 10
            continue

        if min(img.size) <= min_dimension:
            # Sudah di titik minimum (kualitas & dimensi) -- kembalikan
            # hasil terkecil yang bisa dicapai, walau masih di atas target.
            return buf.getvalue()

        new_size = (int(img.width * 0.85), int(img.height * 0.85))
        img = img.resize(new_size, Image.LANCZOS)
        quality = 85


def _compress_pdf_bytes(data, max_bytes, min_dpi=40, min_quality=15):
    import fitz  # PyMuPDF

    dpi, quality = 150, 80
    result = data
    while True:
        src = fitz.open(stream=data, filetype='pdf')
        new_pdf = fitz.open()
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        for page in src:
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes('jpeg', jpg_quality=quality)
            new_page = new_pdf.new_page(width=pix.width, height=pix.height)
            new_page.insert_image(fitz.Rect(0, 0, pix.width, pix.height), stream=img_bytes)
        src.close()

        buf = io.BytesIO()
        new_pdf.save(buf, deflate=True, garbage=4)
        new_pdf.close()
        result = buf.getvalue()

        if len(result) <= max_bytes:
            return result

        if quality > min_quality:
            quality -= 15
        elif dpi > min_dpi:
            dpi = max(min_dpi, int(dpi * 0.75))
            quality = 60
        else:
            # Sudah di titik minimum (dpi & kualitas) -- kembalikan hasil
            # terkecil yang bisa dicapai, walau masih di atas target.
            return result


def compress_uploaded_file(django_file, max_kb=480):
    """Kompres file upload (gambar JPG/PNG atau PDF) supaya <= max_kb.

    Return file baru (ContentFile) kalau berhasil dikompres, atau file
    ASLI (tidak diubah) kalau: sudah cukup kecil, tipenya tidak
    didukung (biar validator lain yang menolak/menerima), atau proses
    kompresi gagal (dicatat ke log, tidak memblokir simpan)."""
    if django_file is None or django_file.size <= max_kb * 1024:
        return django_file

    max_bytes = max_kb * 1024
    name = django_file.name or ''
    ext = _get_extension(name)

    try:
        django_file.seek(0)
        data = django_file.read()

        if ext in IMAGE_EXTENSIONS:
            compressed = _compress_image_bytes(data, max_bytes)
            new_name = name.rsplit('.', 1)[0] + '.jpg'
            logger.info(
                f'Kompres gambar "{name}": {len(data)} -> {len(compressed)} bytes'
            )
            return ContentFile(compressed, name=new_name)

        if ext in PDF_EXTENSIONS:
            compressed = _compress_pdf_bytes(data, max_bytes)
            logger.info(
                f'Kompres PDF "{name}": {len(data)} -> {len(compressed)} bytes'
            )
            return ContentFile(compressed, name=name)

    except Exception:
        logger.exception(f'Gagal kompres file "{name}", pakai file asli')

    django_file.seek(0)
    return django_file
