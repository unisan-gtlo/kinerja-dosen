"""Verifikasi wajah (syarat 2) -- InsightFace/ArcFace (embedding) via ONNX.

Model dimuat SEKALI per proses (lazy singleton, lihat get_face_app) --
memuatnya berat (~beberapa detik + ratusan MB RAM), jangan sampai dimuat
ulang tiap request. Berjalan di CPU (ctx_id=-1); untuk skala ~150 dosen ini
cukup cepat, tidak perlu GPU.

Catatan JUJUR soal liveness: fungsi liveness di sini BARU heuristik
sederhana (persis 1 wajah, skor deteksi cukup tinggi, ukuran wajah wajar
dalam bingkai) -- BUKAN anti-spoof sungguhan (belum bisa membedakan foto
cetak/replay video dari wajah asli). Presensi tetap harus melalui gerbang
skor risiko; kalau nanti dibutuhkan anti-spoof yang lebih kuat, tambahkan
model anti-spoof ONNX terpisah dan panggil dari sini tanpa mengubah
pemanggil (presensi/decision.py).

Embedding disimpan TERENKRIPSI (Fernet, kunci di env FIELD_ENCRYPTION_KEY)
sesuai UU PDP -- lihat presensi/models.py::EnrolmentWajah &
docs/presensi/kebijakanprivasiconsentbiometrik.md.
"""
import numpy as np
from cryptography.fernet import Fernet
from django.conf import settings

VERSI_MODEL_WAJAH = "insightface-buffalo_l"

# Skor deteksi wajah (SCRFD) minimum -- di bawah ini dianggap terlalu tidak
# yakin untuk dipakai (kemungkinan wajah terpotong/blur/sudut ekstrem).
SKOR_DETEKSI_MINIMUM = 0.5

# Tinggi kotak wajah dibanding tinggi gambar -- terlalu kecil berarti wajah
# terlalu jauh dari kamera (juga menyaring beberapa kasus foto-dari-foto).
RASIO_TINGGI_WAJAH_MINIMUM = 0.15

# Kemiripan kosinus minimum antara embedding tersimpan & embedding selfie
# saat ini supaya dianggap "wajah yang sama". Nilai awal, perlu dikalibrasi
# ulang dengan data nyata setelah dipakai beberapa waktu.
SKOR_KEMIRIPAN_MINIMUM = 0.38

_face_app = None


def get_face_app():
    """Singleton FaceAnalysis -- dimuat sekali per proses worker gunicorn."""
    global _face_app
    if _face_app is None:
        from insightface.app import FaceAnalysis

        app = FaceAnalysis(name="buffalo_l")
        app.prepare(ctx_id=-1, det_size=(640, 640))
        _face_app = app
    return _face_app


def _baca_gambar(berkas):
    """Decode file upload (InMemoryUploadedFile/TemporaryUploadedFile) jadi
    array gambar BGR (format yang dipakai OpenCV/InsightFace)."""
    import cv2

    berkas.seek(0)
    data = np.frombuffer(berkas.read(), dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def ekstrak_satu_wajah(berkas_gambar):
    """Deteksi & ekstrak SATU wajah dari file gambar.

    Return (wajah, None) kalau lolos semua pemeriksaan, atau (None, alasan)
    kalau gagal -- alasan pakai kode yang sama dengan
    docs/presensi/spesifikasiapipresensi.md (mis. "liveness_gagal").
    """
    gambar = _baca_gambar(berkas_gambar)
    if gambar is None:
        return None, "foto_tidak_valid"

    daftar_wajah = get_face_app().get(gambar)

    if len(daftar_wajah) != 1:
        # Tidak ada wajah ATAU lebih dari satu wajah -- dua-duanya mencurigakan.
        return None, "liveness_gagal"

    wajah = daftar_wajah[0]
    if wajah.det_score < SKOR_DETEKSI_MINIMUM:
        return None, "liveness_gagal"

    tinggi_wajah = wajah.bbox[3] - wajah.bbox[1]
    if tinggi_wajah / gambar.shape[0] < RASIO_TINGGI_WAJAH_MINIMUM:
        return None, "liveness_gagal"

    return wajah, None


def rata_rata_embedding(daftar_embedding):
    return np.mean(np.stack(daftar_embedding), axis=0)


def kemiripan_kosinus(embedding_a, embedding_b):
    a = np.asarray(embedding_a, dtype=np.float32)
    b = np.asarray(embedding_b, dtype=np.float32)
    penyebut = np.linalg.norm(a) * np.linalg.norm(b)
    if penyebut == 0:
        return 0.0
    return float(np.dot(a, b) / penyebut)


def _fernet():
    kunci = settings.FIELD_ENCRYPTION_KEY
    if isinstance(kunci, str):
        kunci = kunci.encode()
    return Fernet(kunci)


def enkripsi_embedding(embedding):
    data = np.asarray(embedding, dtype=np.float32).tobytes()
    return _fernet().encrypt(data)


def dekripsi_embedding(data_terenkripsi):
    data = _fernet().decrypt(bytes(data_terenkripsi))
    return np.frombuffer(data, dtype=np.float32)
