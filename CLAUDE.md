# CLAUDE.md — Panduan Proyek untuk Claude Code

> File ini dibaca otomatis oleh Claude Code di setiap sesi. Isinya konteks proyek, aturan, dan konvensi.
> Bagian bertanda **[ISI SETELAH AUDIT]** harus diperbarui setelah Claude Code memetakan repositori (lihat "Langkah pertama").

---

## 1. Gambaran Proyek

Aplikasi ini adalah **Portal Kinerja UNISAN** (`kinerja.unisan-g.id`). Kita sedang **menambahkan modul Presensi (absensi)** untuk **Dosen** dan **Pegawai/Staf**, yang diakses via **web dan smartphone**.

Tujuan modul presensi: karyawan bisa absen masuk/pulang dari perangkatnya, **dengan jaminan absen benar-benar dilakukan di kantor/kampus dan oleh orang yang bersangkutan** (anti-curang).

Modul presensi **menempel** pada aplikasi yang sudah ada — memakai ulang data pegawai, autentikasi/login, dan terhubung ke penilaian kinerja. **Jangan menduplikasi** data pegawai; referensikan model yang sudah ada. Data dosen bersumber dari **SIMDA** dan salinannya sudah tersimpan lokal di app **`simda_dosen`** pada portal kinerja — modul presensi mereferensikan model itu (lihat bagian 2.1).

---

## 2. Tech Stack

- **Backend:** Python + Django + Django REST Framework (DRF)
- **Database:** PostgreSQL biasa. ~~PostGIS~~ **tidak dipakai** — GDAL native library tidak tersedia di lingkungan dev proyek ini (lihat hasil audit Bagian 8), jadi cek geofence memakai `latitude`/`longitude` (`FloatField`) + formula **Haversine** murni-Python (`presensi/geo.py`), bukan `django.contrib.gis`/`PointField`. Cukup akurat untuk radius ratusan meter; revisit ke PostGIS kalau nanti ada kebutuhan query spasial yang lebih kompleks.
- **Tugas asinkron:** Celery + Redis (untuk proses berat: pencocokan wajah, notifikasi, laporan)
- **Face recognition:** InsightFace/ArcFace (embedding) + model anti-spoof/liveness ONNX
- **Frontend:** PWA (Web App Manifest + Service Worker — belum ada, perlu ditambahkan untuk presensi). Framework UI portal kinerja saat ini: **server-rendered Django templates + Tabler UI (Bootstrap-based, dimuat via CDN) + JS vanilla**. Tidak ada HTMX/Alpine/React yang terpasang — ikuti pola template+Tabler yang sama untuk halaman presensi non-PWA (mis. dashboard admin/HR).
- **Deployment:** Railway (Nixpacks + Procfile, lihat `config/nixpacks.toml` & `config/Procfile`) dengan WhiteNoise untuk static files. HTTPS/HSTS hanya aktif otomatis saat `RAILWAY_ENVIRONMENT` terdeteksi (lihat `config/settings.py`).

**[ISI SETELAH AUDIT]**
- Versi Django: **6.0.4** (di virtualenv proyek, `venv/`) · Versi Python: **3.12.3**. ⚠️ Ada instalasi Django global (5.1.15) di luar venv — **selalu jalankan lewat `venv/Scripts/python.exe` atau aktifkan venv dulu**, jangan pakai `python` sistem.
- App data dosen yang sudah ada: **`simda_dosen`**, model **`DataDosen`** (BUKAN `Dosen` — draft `presensi/models.py` & docs masih menyebut `simda_dosen.Dosen`, ini perlu dikoreksi). Field kunci: **`nidn`** = `CharField(max_length=20, unique=True, db_index=True)` — **sudah `unique=True`**, syarat FK/lookup terpenuhi. Model ini **`managed=False`**, tabel fisiknya `master"."data_dosen` di **database terpisah `unisan_db`** (bukan `sikd_db`), diakses lewat koneksi kedua `DATABASES['simda']` + `DATABASE_ROUTERS = ['config.db_router.SimdaRouter']`.
  - ⚠️ **Temuan penting:** `SimdaRouter.allow_relation()` (`config/db_router.py`) secara eksplisit **menolak relasi lintas-app** antara `simda_dosen` dan app lain (hanya mengizinkan relasi bila KEDUA sisi sama-sama `simda_dosen`). Karena `sikd_db` dan `unisan_db` adalah **database Postgres yang berbeda** (bukan sekadar schema berbeda), **`ForeignKey` biasa dari `presensi` ke `simda_dosen.DataDosen` tidak bisa bekerja** — Postgres tidak mendukung FK/JOIN lintas database, dan router memang sengaja melarangnya.
  - **Sudah diperbaiki** (lihat `presensi/models.py`, `presensi/utils.py`): semua field dosen di `presensi` sekarang `CharField nidn` biasa (bukan `ForeignKey`), diresolve manual lewat `get_dosen_by_nidn()` yang memanggil `DataDosen.objects.using('simda').filter(nidn=...)` — pola yang sama dipakai `profil/views.py` (helper `get_simda_dosen_or_none`/`dapat_kelola_nidn`).
- Mekanisme autentikasi: **Django session-based auth** (`accounts.User` custom model, `AUTH_USER_MODEL`), login via form username/password + captcha + lockout `django-axes` (`accounts/views.py::login_view`). Ditambah **`SSOAutoLoginMiddleware`** (`accounts/sso_middleware.py`) yang JIT-provisioning user dari cookie SSO eksternal (`sso_token`, diverifikasi ke `SSO_VERIFY_URL`). **Belum ada DRF maupun JWT** di proyek ini (`djangorestframework` & `djangorestframework-simplejwt` tidak ada di `requirements.txt`) — perlu ditambahkan khusus untuk API presensi (mobile/PWA butuh token, bukan cookie session SSO).

---

## 2.1 Sumber Data Dosen & Integrasi SIMDA (PENTING)

- **Master data dosen/pegawai ada di SIMDA** (database PostgreSQL tersendiri).
- Portal kinerja **sudah menyimpan salinan lokal** data dosen tersebut lewat app **`simda_dosen`** (dapat dilihat di `/admin/simda_dosen/`).
- **Modul presensi TIDAK menyambung langsung ke SIMDA** dan **TIDAK menduplikasi** data dosen. Presensi mereferensikan dosen lewat **NIDN**.
- Presensi hanya menyimpan **hasil absensi** di tabelnya sendiri; identitas dosen selalu diambil dari `simda_dosen`.
- Data dosen bersifat **read-only** bagi presensi — **jangan pernah menulis/mengubahnya** dari modul presensi.
- Hasil presensi terhubung ke penilaian kinerja lewat kunci dosen yang sama (NIDN).

**[HASIL AUDIT — koreksi penting, sudah diterapkan di `presensi/models.py`]**
- Nama model: **`simda_dosen.DataDosen`** (bukan `Dosen`). Field kunci **`nidn`** sudah `CharField(unique=True, db_index=True)`.
- **`DataDosen` fisiknya di database terpisah (`unisan_db`, alias koneksi `simda`), bukan `sikd_db`.** `config/db_router.py::SimdaRouter.allow_relation()` **menolak** relasi lintas-app ke `simda_dosen`. Akibatnya **`ForeignKey` lintas app dari `presensi` ke `simda_dosen.DataDosen` TIDAK BISA dipakai** (Postgres tidak bisa JOIN/FK lintas database, dan router memang sengaja memblokirnya).
- **Pendekatan yang dipakai (ikuti pola `profil` app):** field `nidn` di semua tabel presensi (`Presensi`, `JadwalKerja`, `Perangkat`, `EnrolmentWajah`, `IzinCuti`, `LogKecurangan`) berupa **`CharField(max_length=20, db_index=True)` biasa**, BUKAN `ForeignKey`. Untuk mengambil data dosen, `presensi.utils.get_dosen_by_nidn()` query `DataDosen` lewat `.objects.using('simda')` (routing otomatis via `SimdaRouter` berdasarkan `app_label`), mirip helper `get_simda_dosen_or_none` di `profil/views.py`. Validasi bahwa NIDN benar-benar ada di `simda_dosen` perlu dilakukan di level aplikasi (serializer/form) saat API dibangun — belum ada di Tahap 2 (Model & DB) ini.

---

## 3. Model Presensi — Aturan Inti

Presensi diterima **HANYA jika DUA syarat lolos** (gerbang **DAN**):

1. **Cek Lokasi** — koordinat GPS berada di dalam radius geofence `LokasiKantor` (dihitung server-side dengan formula Haversine, lihat `presensi/geo.py` — bukan PostGIS, lihat Bagian 2 & 8).
2. **Verifikasi Wajah** — selfie cocok dengan embedding hasil enrolment **DAN** lolos liveness (bukan foto/video).

**Opsi tambahan (feature flag per lokasi, default MATI):**
- **QR dinamis** — token acak berumur ±60 detik, sekali pakai.
- **Cek Wi-Fi/IP** — perangkat terhubung ke SSID/IP jaringan kantor.

Bila flag opsi menyala, ia menjadi sinyal tambahan pada mesin keputusan. Rancang mesin keputusan **modular** agar syarat bisa dicolok/dicabut lewat konfigurasi, bukan hardcode.

### Mesin skor risiko
Setiap presensi diberi `skor_risiko` dari gabungan sinyal (lokasi, wajah, perangkat, opsi). Keputusan:
- **Risiko rendah** → otomatis sah
- **Risiko sedang** → ditandai (`ditandai=True`) untuk tinjauan HR
- **Risiko tinggi** → ditolak + dicatat di `LogKecurangan`

---

## 4. Prinsip Keamanan (WAJIB dipatuhi di semua kode)

- **Server adalah otoritas.** Klien hanya mengirim data mentah (koordinat, foto, token). **Semua keputusan valid/tidak dihitung di server**, jangan pernah percaya flag "valid" dari klien.
- **Waktu dari server.** Timestamp absen memakai waktu server, bukan waktu perangkat.
- **Rahasia tidak boleh di kode.** Semua kredensial (password DB, `SECRET_KEY`, kunci API) lewat variabel lingkungan / file `.env`. Pastikan `.env` ada di `.gitignore`. **Jangan pernah commit rahasia.**
- **Data biometrik = data pribadi spesifik (UU PDP No. 27/2022).** Simpan **face embedding terenkripsi**, bukan foto mentah bila memungkinkan; batasi retensi; sediakan jalur penghapusan.
- **Semua endpoint butuh autentikasi** (JWT) + **rate-limiting** + validasi input.
- **HTTPS wajib** (kamera & GPS di browser hanya aktif di koneksi aman).

---

## 5. Konvensi Kode

- Ikuti gaya & struktur yang sudah ada di portal kinerja (lihat hasil audit). Konsistensi lebih penting daripada preferensi pribadi.
- **Komentar dan pesan untuk pengguna ditulis dalam Bahasa Indonesia.** Nama variabel/fungsi boleh Inggris standar.
- **Setiap fitur wajib disertai unit test.** Sertakan kasus normal DAN kasus kecurangan (di luar radius, wajah tidak cocok, token kedaluwarsa).
- Proses berat (pencocokan wajah, enrolment) dijalankan asinkron via Celery bila memungkinkan.
- Modul presensi berada di Django app tersendiri bernama `presensi`.
- Migrasi database selalu disertakan dan diperiksa sebelum dijalankan.

---

## 6. Alur Kerja & Aturan untuk Claude Code

- **Kerja per potongan kecil.** Satu fitur per kali; jangan menulis banyak fitur sekaligus dalam satu perubahan besar.
- **Selalu jelaskan rencana singkat sebelum menulis kode**, lalu tulis kode + test.
- **Jangan menjalankan perintah destruktif** (drop database, hapus migrasi, `git push --force`, hapus file massal) tanpa konfirmasi eksplisit.
- **Jangan mengubah file di luar cakupan tugas** yang diminta.
- Bila asumsi tentang struktur portal kinerja belum pasti, **tanya atau periksa dulu** — jangan menebak.
- Setelah membuat fitur, **ingatkan untuk menjalankan test dan meninjau diff** sebelum commit.

---

## 7. Perintah Penting

```bash
# Aktifkan venv proyek dulu (JANGAN pakai python sistem — versi Django beda)
venv\Scripts\activate

# Migrasi database
python manage.py makemigrations
python manage.py migrate

# Menjalankan test modul presensi
python manage.py test presensi

# Menjalankan server pengembangan
python manage.py runserver

# Worker Celery (proses asinkron) — Celery/Redis BELUM terpasang, lihat catatan Bagian 8
celery -A config worker -l info
```
Nama proyek Django (untuk `-A`): **`config`** (lihat `config/settings.py`, `config/wsgi.py`).

---

## 8. Langkah Pertama (sekali di awal)

Sebelum menulis kode fitur, minta Claude Code:
1. Memetakan struktur repositori: versi Django/Python, daftar app, model pegawai, cara autentikasi, framework frontend.
2. Mengisi semua bagian **[ISI SETELAH AUDIT]** di file ini.
3. Mengonfirmasi bahwa PostGIS bisa diaktifkan di database.

Baru setelah itu lanjut ke Tahap 2 (Model & DB) pada panduan coding.

**[HASIL AUDIT — status PostGIS/GDAL, per 2026-07-28]**
- **Belum bisa dikonfirmasi aktif**, dan **keputusan: tidak dipakai untuk sekarang.** Service `postgresql-x64-18` di mesin lokal berstatus **Stopped** (Claude Code tidak bisa start service Windows tanpa hak admin), dan percobaan koneksi (lewat Django maupun `psql` langsung) memakai kredensial di `.env` gagal (`password authentication failed for user "postgres"`) — perlu dicek langsung oleh yang punya akses DB. Mengimpor `django.contrib.gis` juga gagal (`Could not find the GDAL library` — GDAL native library tidak terpasang di mesin Windows ini).
- **Karena itu presensi TIDAK memakai PostGIS/GDAL/`PointField`.** Sebagai gantinya: koordinat disimpan sebagai `latitude`/`longitude` (`FloatField`) biasa, jarak ke `LokasiKantor` dihitung dengan formula **Haversine** murni-Python di `presensi/geo.py`. Ini menghindari ketergantungan pada GDAL sepenuhnya (baik di dev maupun deploy) dan cukup akurat untuk geofence berskala ratusan meter — cocok untuk MVP dan untuk yang baru pertama kali membuat model bergeo-lokasi.
- App `presensi` **sudah** dijadikan app Django lengkap dan didaftarkan di `INSTALLED_APPS` (`__init__.py`, `apps.py`, model diperbaiki, `admin.py`, `tests.py`, migrasi awal `0001_initial` sudah dibuat — lihat `presensi/migrations/`). **Migrasi belum dijalankan** (`python manage.py migrate`) karena Postgres lokal tidak bisa diakses (lihat poin di atas) — jalankan sendiri setelah DB lokal aktif.
- Paket lain yang disebut di CLAUDE.md Bagian 2 tapi **belum ada di `requirements.txt`**: `djangorestframework`, `djangorestframework-simplejwt` (atau setara), `celery`, `redis`, `insightface`/`onnxruntime` (face recognition), library encryption field (mis. `django-cryptography` — `cryptography` sendiri sudah terpasang jadi Fernet manual juga bisa). Semua ini perlu ditambahkan bertahap sesuai fitur yang dikerjakan (Tahap 3 dst).
- Yang **sudah** cocok dengan kebutuhan presensi: `psycopg2-binary` ✓, `django-ratelimit` ✓ (rate-limiting), `django-axes` ✓ (lockout, bisa dipakai pola serupa untuk device/percobaan presensi), `cryptography` ✓ (untuk enkripsi embedding).

---

## 9. Urutan Pengembangan (ringkas)

Model & DB → API + Cek Lokasi (syarat 1) → Verifikasi Wajah (syarat 2) → Gerbang 2 syarat + skor risiko → Opsi QR & Wi-Fi (feature flag) → PWA (alur 2 langkah) → Dashboard admin/HR → Test, keamanan, deploy.

**MVP dulu:** absen dengan cek lokasi saja agar cepat bisa dicoba, baru tambahkan verifikasi wajah.

**[STATUS per 2026-07-28]** Model & DB ✅, API + Cek Lokasi ✅ (sudah dites live di `kinerja.unisan-g.id`, endpoint `POST /api/presensi/masuk|pulang`, `GET /api/presensi/status-hari-ini`, JWT via `djangorestframework-simplejwt`), halaman web dasar untuk coba-coba ✅ (`/presensi/`, `templates/presensi/absen.html` — bukan PWA installable, cuma halaman biasa dalam portal, dipanggil lewat sesi Django), dashboard tinjauan HR/admin ✅ (`/presensi/tinjau/`, `templates/presensi/tinjau.html` — daftar presensi `ditandai=True`, tombol Setujui/Tolak, dibatasi ke role `admin` + `dekan/wadek/kaprodi/sekprodi/operator` dan di-scope per fakultas/prodi lewat `simda_dosen.utils.dapat_kelola_nidn`, sama seperti pola `profil`). Belum: Verifikasi Wajah (syarat 2 — sampai ini ada, semua presensi yang lolos cek lokasi tetap `tingkat_risiko=sedang` + `ditandai=True`, belum otomatis sah penuh), opsi QR/Wi-Fi, PWA installable (manifest + service worker).
