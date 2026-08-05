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

Anti-spoof tahap awal (2026-08-05): `deteksi_spoofing()` di bawah menambah
2 sinyal klasik berbasis OpenCV/NumPy (BUKAN model ML terpisah -- sengaja
dipilih supaya tidak perlu mengunduh file model dari luar, dan berjalan
sama di semua jenis HP karena murni pemrosesan gambar di server):
- Variansi Laplacian (ketajaman) -- foto hasil re-capture (dicetak atau
  difoto ulang dari layar HP lain) biasanya kehilangan detail halus
  dibanding wajah asli langsung di depan kamera.
- Energi frekuensi tinggi (indikasi pola moire) -- muncul kalau wajah
  difoto dari LAYAR HP/monitor lain (replay), akibat interferensi grid
  piksel layar dengan grid sensor kamera.
Kedua ambang batasnya (`SKOR_KETAJAMAN_*`/`SKOR_MOIRE_*`) BELUM
dikalibrasi dengan data foto sungguhan -- sama seperti catatan kalibrasi
SKOR_KEMIRIPAN_MINIMUM di bawah, perlu ditinjau ulang setelah dipakai
beberapa waktu. Karena belum teruji, ambang "curiga" (bukan "tolak")
sengaja dibuat jauh lebih longgar -- lihat presensi/decision.py untuk
bagaimana ini masuk ke skor_risiko (tingkat sedang, ditinjau HR) alih-alih
langsung menolak presensi yang jujur.

Embedding disimpan TERENKRIPSI (Fernet, kunci di env FIELD_ENCRYPTION_KEY)
sesuai UU PDP -- lihat presensi/models.py::EnrolmentWajah &
docs/presensi/kebijakanprivasiconsentbiometrik.md.
"""
from dataclasses import dataclass

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

# Ambang anti-spoof tahap awal -- BELUM dikalibrasi dengan data sungguhan
# (lihat catatan di docstring modul). SENGAJA tidak ada tingkat "tolak
# langsung" -- foto asli dalam kondisi wajar (cahaya redup, wajah dekat
# kamera dengan kulit halus, dsb.) bisa saja punya skor ketajaman/moire
# yang mirip dengan foto rekayasa selama belum dikalibrasi dengan data
# sungguhan, jadi kalau langsung menolak berisiko salah tolak dosen yang
# jujur. Presensi yang lewat ambang "CURIGA" ini TETAP DITERIMA, cuma
# ditandai untuk tinjauan HR (tingkat risiko sedang) -- lihat
# presensi/decision.py::verifikasi_wajah & presensi/views.py.
SKOR_KETAJAMAN_CURIGA = 60.0
# skor_moire = rasio puncak/rata-rata energi frekuensi tinggi -- tekstur
# kulit/noise wajar diuji berkisar ~3-5, pola periodik (moire sungguhan)
# diuji berkisar ribuan -- 20 memberi margin aman jauh di atas tekstur
# wajar, jauh di bawah pola moire nyata.
SKOR_MOIRE_CURIGA = 20.0

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


def _potong_wajah(gambar, wajah):
    """Potong region kotak wajah (bbox) dari gambar penuh -- anti-spoof di
    bawah dianalisis di area wajah saja, bukan seluruh foto (latar
    belakang tidak relevan dan bisa mengaburkan sinyalnya)."""
    x1, y1, x2, y2 = [int(v) for v in wajah.bbox]
    x1, y1 = max(x1, 0), max(y1, 0)
    x2, y2 = min(x2, gambar.shape[1]), min(y2, gambar.shape[0])
    return gambar[y1:y2, x1:x2]


def skor_ketajaman(potongan_wajah):
    """Variansi Laplacian (ketajaman) -- foto hasil re-capture (dicetak
    atau difoto ulang dari layar HP lain) biasanya kehilangan detail halus
    (pori kulit, kerutan) dibanding wajah asli langsung di depan kamera,
    variansinya cenderung lebih rendah."""
    import cv2

    abu = cv2.cvtColor(potongan_wajah, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(abu, cv2.CV_64F).var())


def skor_moire(potongan_wajah):
    """Rasio puncak terhadap rata-rata energi frekuensi tinggi (indikasi
    pola moire) -- muncul kalau wajah difoto dari LAYAR HP/monitor lain
    (replay), akibat interferensi grid piksel layar dengan grid sensor
    kamera. Komponen frekuensi rendah (bentuk wajah wajar) dibuang dulu
    supaya tidak ikut terhitung.

    SENGAJA pakai rasio puncak/rata-rata, BUKAN rata-rata energi mentah --
    tekstur kulit asli (noise berbutir halus, wajar) juga punya energi
    frekuensi tinggi yang lumayan besar tapi TERSEBAR RATA di semua
    frekuensi, sedangkan moire (pola berulang dari grid piksel layar)
    membentuk beberapa PUNCAK TAJAM yang menonjol jauh di atas baseline-nya
    -- rasio puncak/rata-rata inilah yang membedakan keduanya, bukan
    besarnya energi itu sendiri."""
    import cv2

    abu = cv2.cvtColor(potongan_wajah, cv2.COLOR_BGR2GRAY).astype(np.float32)
    f = np.fft.fft2(abu)
    magnitude = np.abs(np.fft.fftshift(f))

    tinggi, lebar = magnitude.shape
    tengah_y, tengah_x = tinggi // 2, lebar // 2
    radius_buang = max(min(tinggi, lebar) // 8, 1)
    magnitude[
        max(tengah_y - radius_buang, 0):tengah_y + radius_buang,
        max(tengah_x - radius_buang, 0):tengah_x + radius_buang,
    ] = 0

    rata_rata = magnitude.mean()
    if rata_rata < 1e-6:
        return 0.0
    return float(magnitude.max() / rata_rata)


@dataclass
class HasilAntiSpoof:
    dicurigai: bool
    skor_ketajaman: float
    skor_moire: float


def deteksi_spoofing(gambar, wajah) -> HasilAntiSpoof:
    """Anti-spoof tahap awal (lihat catatan kalibrasi di docstring modul)
    -- TIDAK PERNAH menolak presensi, cuma menandai `dicurigai=True` kalau
    salah satu sinyal (ketajaman atau moire) berada di zona mencurigakan.
    Pemanggil (presensi/decision.py) yang memutuskan bagaimana `dicurigai`
    dipakai (masuk skor_risiko tingkat sedang, bukan penolakan)."""
    potongan = _potong_wajah(gambar, wajah)
    if potongan.size == 0:
        return HasilAntiSpoof(False, 0.0, 0.0)

    ketajaman = skor_ketajaman(potongan)
    moire = skor_moire(potongan)
    dicurigai = ketajaman < SKOR_KETAJAMAN_CURIGA or moire > SKOR_MOIRE_CURIGA
    return HasilAntiSpoof(dicurigai, ketajaman, moire)


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
