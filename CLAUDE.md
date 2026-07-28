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
- **Tugas asinkron:** ~~Celery + Redis~~ **belum dipakai** — enrolment wajah (proses terberat) untuk sekarang dijalankan **sinkron** dalam request (skala ~150 dosen, enrolment jarang dilakukan, latensi beberapa detik dianggap wajar). Redis/Celery belum terpasang di VPS produksi; revisit kalau ternyata jadi masalah nyata (bukan Nixpacks/Railway — lihat catatan Deployment di bawah).
- **Face recognition:** InsightFace/ArcFace (`buffalo_l`, jalan di CPU via `onnxruntime`) — **sudah aktif** (`presensi/face.py`). Liveness/anti-spoof **BARU heuristik sederhana** (1 wajah terdeteksi, skor deteksi cukup, ukuran wajah wajar) — belum model anti-spoof ONNX terpisah seperti rencana awal.
- **Frontend:** PWA khusus `/presensi/` — **sudah ada** (`static/presensi-manifest.json` + service worker minimal di `/presensi/sw.js`, lihat § 9). Framework UI portal kinerja saat ini: **server-rendered Django templates + Tabler UI (Bootstrap-based, dimuat via CDN) + JS vanilla**. Tidak ada HTMX/Alpine/React yang terpasang — ikuti pola template+Tabler yang sama untuk halaman presensi non-PWA (mis. dashboard admin/HR).
- **Deployment:** ~~Railway~~ **VPS bare-metal** (`kinerja.unisan-g.id` di server `unisan-g`) — Nginx (proxy ke Unix socket) → `gunicorn-sikd.service` (systemd, jalan sebagai `root`) → kode di `/var/www/sikd` (clone git repo yang sama, di-update lewat `update.sh`: `git pull` + `pip install` + `migrate` + `collectstatic` + restart service, **dijalankan pakai `sudo`** karena file dimiliki `root`). `config/nixpacks.toml`/`Procfile` masih ada di repo tapi **tidak dipakai** untuk deployment aktual — sisa dari rencana awal, boleh diabaikan atau dihapus kalau memang tidak akan pindah ke Railway.

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
- **Modul presensi TIDAK menyambung langsung ke SIMDA** dan **TIDAK menduplikasi** data dosen.
- Presensi hanya menyimpan **hasil absensi** di tabelnya sendiri; identitas dosen (nama+gelar, fakultas/prodi versi SIMDA) diambil dari `simda_dosen` lewat NIDN saat dibutuhkan.
- Data dosen bersifat **read-only** bagi presensi — **jangan pernah menulis/mengubahnya** dari modul presensi.
- Hasil presensi terhubung ke penilaian kinerja lewat kunci yang sama (NIDN, diakses lewat `user.nidn`).

**[HASIL AUDIT — koreksi penting, sudah diterapkan di `presensi/models.py`]**
- Nama model: **`simda_dosen.DataDosen`** (bukan `Dosen`). Field kunci **`nidn`** sudah `CharField(unique=True, db_index=True)`.
- **`DataDosen` fisiknya di database terpisah (`unisan_db`, alias koneksi `simda`), bukan `sikd_db`.** `config/db_router.py::SimdaRouter.allow_relation()` **menolak** relasi lintas-app ke `simda_dosen`. Akibatnya **`ForeignKey` lintas app dari `presensi` ke `simda_dosen.DataDosen` TIDAK BISA dipakai** (Postgres tidak bisa JOIN/FK lintas database, dan router memang sengaja memblokirnya).

**[MIGRASI KUNCI IDENTITAS — selesai per 2026-07-29]** Kunci identitas presensi sudah **diganti dari `nidn` (CharField) menjadi `user` (ForeignKey ke `accounts.User`)** di semua 6 tabel (`Presensi`, `JadwalKerja`, `Perangkat`, `EnrolmentWajah`, `IzinCuti`, `LogKecurangan`) — supaya presensi mencakup **staf/tendik juga** (staf tidak punya NIDN, jadi tidak bisa terus dikunci NIDN). `accounts.User` ada di database yang SAMA (`sikd_db`) dengan presensi, jadi FK biasa aman dipakai di sini (beda dengan `simda_dosen.DataDosen` yang di database terpisah). Untuk mengayakan data dosen, ambil NIDN lewat `user.nidn` lalu panggil `presensi.utils.get_dosen_by_nidn(user.nidn)` seperti sebelumnya — staf cukup pakai field `accounts.User` langsung (tidak ada equivalent SIMDA untuk staf).

Migrasi database dibuat 3 tahap (lihat `presensi/migrations/0002`–`0004`) supaya aman untuk data produksi yang sudah ada: (1) tambah field `user` nullable, (2) migrasi data — backfill `user` dari pencocokan `nidn` lama ke `accounts.User.nidn`, (3) wajibkan `user` + hapus field `nidn`/`approver` lama — **tahap 3 sengaja dipisah dan HARUS diverifikasi dulu** (lihat docstring di `0003_backfill_user_dari_nidn.py`) sebelum dijalankan, supaya tidak gagal kalau ada baris yang NIDN-nya tidak cocok dengan `accounts.User` mana pun.

Cakupan yang BENAR-BENAR tampil di dashboard/rekap presensi saat ini **masih dosen-only** (lewat `get_dosen_queryset` dari app `laporan`, dipakai di `presensi/views.py`) — skema sudah siap untuk staf, tapi UI/query di lapisan views belum diperluas untuk menampilkan staf. Ini pekerjaan lanjutan yang terpisah (ganti sumber queryset-nya di views.py), bukan perubahan skema lagi.

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

**[STATUS implementasi gerbang, per 2026-07-28]** Gerbang-DAN (lokasi + wajah) sudah aktif penuh (`presensi/decision.py`, `presensi/views.py`), tapi saat ini masih **biner**: lolos KEDUA syarat → langsung risiko rendah (otomatis sah, `ditandai=False`); gagal salah satu → langsung ditolak (tidak ada baris Presensi dibuat, cuma tercatat `LogKecurangan`). Tingkat **sedang** (ditandai untuk tinjauan HR) belum benar-benar dipakai untuk presensi baru — kalau nanti dibutuhkan nuansa (mis. skor kemiripan wajah pas-pasan di atas ambang tetap ditandai, bukan langsung disahkan), itu perbaikan lanjutan di skor_risiko, belum diterapkan. Liveness saat ini **BARU heuristik sederhana** (1 wajah terdeteksi, skor deteksi cukup, ukuran wajah wajar) — **BUKAN** anti-spoof sungguhan; lihat `presensi/face.py` untuk detail & catatan upgrade.

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

**[STATUS per 2026-07-28]** Model & DB ✅, API + Cek Lokasi ✅ (sudah dites live di `kinerja.unisan-g.id`, endpoint `POST /api/presensi/masuk|pulang`, `GET /api/presensi/status-hari-ini`, JWT via `djangorestframework-simplejwt`), halaman web dasar untuk coba-coba ✅ (`/presensi/`, `templates/presensi/absen.html` — bukan PWA installable, cuma halaman biasa dalam portal, dipanggil lewat sesi Django), dashboard tinjauan HR/admin ✅ (`/presensi/tinjau/`, `templates/presensi/tinjau.html` — daftar presensi `ditandai=True`, tombol Setujui/Tolak, dibatasi ke role `admin` + `dekan/wadek/kaprodi/sekprodi/operator` dan di-scope per fakultas/prodi lewat `simda_dosen.utils.dapat_kelola_nidn`, sama seperti pola `profil`), Verifikasi Wajah ✅ (syarat 2 — `presensi/face.py`, InsightFace `buffalo_l` di CPU, embedding terenkripsi Fernet, endpoint `POST /api/presensi/enrolment-wajah` + halaman `/presensi/enrolment/`; gerbang-DAN penuh aktif di `masuk`/`pulang`: lolos keduanya → otomatis `rendah`, gagal salah satu → ditolak + `LogKecurangan`, lihat catatan biner/liveness-heuristik di Bagian 3), PWA installable ✅ (`static/presensi-manifest.json`, service worker minimal disajikan di `/presensi/sw.js` — sengaja bukan lewat static/WhiteNoise, supaya cakupannya otomatis `/presensi/*` tanpa header `Service-Worker-Allowed` tambahan di Nginx; ikon dari logo kampus yang sudah ada, `static/img/kampus.png`; tanpa caching offline berat karena GPS/kamera tetap butuh live), Dashboard admin ✅ (`/presensi/dashboard/` — KPI hari ini, tren 6 hari via Chart.js, keterlambatan teratas; `/presensi/data/` — tabel harian 1-baris-per-dosen termasuk yang belum absen, filter fakultas/prodi; ekspor Excel di `/presensi/data/ekspor/` pakai gaya/pola yang sama dengan app `laporan`; logika ada di `presensi/rekap.py`, dipakai ulang oleh view & ekspor).

**[KEPUTUSAN & CATATAN PENTING per 2026-07-28, dari diskusi mockup UI]**
- **Portal TETAP menempel di SIKD**, tidak dipisah jadi aplikasi/domain sendiri — sudah diputuskan setelah menimbang mockup terpisah, alasan lengkap ada di riwayat percakapan (reuse auth/SSO/SIMDA-integration yang sudah ada, mockup itu sendiri berasumsi domain yang sama).
- ✅ **Fondasi staf SELESAI per 2026-07-29** — skema presensi sudah dikunci `user` (`ForeignKey` ke `accounts.User`), bukan `nidn` lagi, lihat detail migrasi di Bagian 2.1. Yang MASIH `dosen-only`: dashboard (`/presensi/dashboard/`) dan tabel data (`/presensi/data/`) di `presensi/views.py` masih memanggil `get_dosen_queryset` (dosen-only) dari app `laporan` — perluasan ke staf tinggal ganti sumber queryset user-nya di sana, TIDAK perlu ubah skema/model lagi.
- ⚠️ **Deteksi mock-GPS/fake-location sungguhan TIDAK BISA dipenuhi lewat PWA/web** (browser tidak pernah mengekspos status mock-location ke JavaScript) — butuh aplikasi native kalau ini jadi kebutuhan wajib. User sudah konfirmasi **belum wajib** sekarang, PWA/web diterima apa adanya untuk tahap ini.
- **Pengajuan Izin/Sakit/Dinas mandiri BELUM ada** — model `IzinCuti` sudah ada sejak Tahap 2, tapi cuma bisa dikelola manual lewat Django admin (`/admin/presensi/izincuti/`), belum ada endpoint/halaman self-service maupun alur persetujuan atasan. Ini penting diselesaikan **sebelum** laporan rekap bulanan (dasar penggajian) dibangun, supaya bisa membedakan "tidak hadir karena izin" vs "Alpa tanpa keterangan".
- **Kelompok Presensi & Jam Kerja (Dosen 08.00-14.00 Senin-Sabtu vs Pejabat 08.00-16.00) — SEDANG DIANALISIS, belum diimplementasikan.** Keputusan yang sudah diambil: (1) kelompok ditentukan **otomatis dari role akun** (role='dosen' → kelompok Dosen; role dekan/wadek/kaprodi/sekprodi/rektorat/biro → kelompok Pejabat), (2) kelompok yang berlaku **di-snapshot per baris Presensi** saat kejadian (bukan selalu live dari role saat ini) supaya histori tidak berubah kalau jabatan seseorang berubah nanti — penting untuk akurasi dasar penggajian, (3) absen di hari non-kerja/libur **tetap diterima seperti biasa** tanpa hitungan telat dan tidak masuk hitungan wajib kerja bulanan. Rancangan model: `KelompokPresensi` (nama, hari_kerja, jam_masuk, jam_pulang, toleransi_menit) + `HariLibur` (tanggal, keterangan, jenis) — keduanya BELUM dibuat. Lokasi laporan rekap bulanan (app `laporan` yang sudah ada vs halaman baru di `presensi`) **belum diputuskan**, user masih akan menambah catatan.
