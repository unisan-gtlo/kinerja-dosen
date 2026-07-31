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
- ✅ **Pengajuan Izin/Sakit/Dinas mandiri SELESAI per 2026-07-29** — `/presensi/izin/` (form pengajuan + riwayat pengajuan pribadi) dan `/presensi/izin/tinjau/` (persetujuan atasan, scoping sama seperti Tinjau Presensi lewat `accounts.User.dapat_kelola`). `IzinCuti.approver` sudah jadi FK ke `accounts.User` (bukan lagi CharField "NIDN/ID atasan").
- ✅ **Kelompok Presensi & Jam Kerja (Dosen 08.00-14.00 Senin-Sabtu vs Pejabat 08.00-16.00) SELESAI per 2026-07-29** — model `KelompokPresensi` (`nama`, `roles` ArrayField, `hari_kerja` ArrayField, `jam_masuk`, `jam_pulang`, `toleransi_menit`, `aktif`) dan `HariLibur` (`tanggal` unik, `keterangan`, `jenis`) ditambahkan di `presensi/models.py`, migrasi `0005_harilibur_kelompokpresensi_presensi_kelompok` + data awal `0006_seed_kelompok_presensi` (seed "Dosen" 08.00-14.00 roles=`["dosen"]` & "Pejabat" 08.00-16.00 roles=`["dekan","wadek","kaprodi","sekprodi","rektorat","biro"]`, keduanya Senin-Sabtu). Perlu `'django.contrib.postgres'` ditambahkan ke `INSTALLED_APPS` (`config/settings.py`) supaya `ArrayField` bisa dipakai (`postgres.E005`). Mesin keputusan (`presensi/decision.py::resolve_kelompok(user)` + `tentukan_status_waktu(lokasi, jam, kelompok=None, tanggal=None)`) memetakan role akun ke kelompok otomatis, memprioritaskan jam kelompok di atas jam `LokasiKantor` (fallback kalau role belum dipetakan), dan mengembalikan `HADIR` tanpa hitungan telat untuk `HariLibur` maupun hari di luar `hari_kerja` kelompok (mis. Minggu). `AbsenMasukView` (`presensi/views.py`) sudah men-snapshot `kelompok` yang berlaku ke `Presensi.kelompok` saat absen masuk (bukan FK live ke role saat ini — lihat docstring `KelompokPresensi`, penting untuk akurasi dasar penggajian kalau jabatan berubah nanti). Admin diregistrasi (`KelompokPresensiAdmin`, `HariLiburAdmin`) + test ditambahkan (`ResolveKelompokTest`, `TentukanStatusWaktuTest`, `SeedKelompokPresensiTest`, plus 1 test snapshot di `AbsenMasukAPITest`) — **belum dijalankan** (Postgres lokal masih tidak bisa diakses, lihat Bagian 8), perlu dites di VPS setelah deploy. Lokasi laporan rekap bulanan (app `laporan` vs halaman baru di `presensi`) **masih belum diputuskan**, ditunda ke pembahasan berikutnya.

**[POLESAN UI MOBILE — Tingkat 1 selesai per 2026-07-29]** Terinspirasi mockup UI yang diberikan user (bukan dikerjakan sama persis — beberapa elemen mockup SENGAJA tidak ditiru, lihat alasan di bawah). Yang sudah ditambahkan ke `templates/presensi/absen.html`: header sapaan personal (nama+inisial avatar+pill role/fakultas, dihitung di `presensi/views.py::halaman_absen`), jam digital + tanggal berjalan (live, JS), alur 2-langkah dengan indikator progres (Lokasi → Wajah — BUKAN 3 langkah termasuk QR seperti mockup, karena QR belum diimplementasikan), visual lingkaran geofence dekoratif (CSS, bukan peta sungguhan), kartu "Berhasil" dengan ringkasan (waktu/lokasi/status/tingkat risiko) menggantikan alert biasa.

**Sengaja TIDAK ditiru dari mockup** (lihat analisis lengkap di riwayat percakapan): (1) chip "Lokasi palsu (mock): Tidak terdeteksi" — PWA/web tidak bisa membuktikan klaim itu jujur (browser tidak expose status mock-location ke JS), jadi tidak ditampilkan supaya tidak menyesatkan pengguna; (2) ringkasan bulanan Hadir/Telat/Izin/Alpa di beranda — Izin & Alpa belum bisa dihitung akurat (logika alpa belum ada), ditunda.

**[TINGKAT 2 UI MOBILE — selesai per 2026-07-29]** Tombol Absen Pulang dibedakan warnanya (hijau) dari Absen Masuk (biru). Bottom navigation bar (`templates/presensi/_bottom_nav.html`, `d-md-none` — cuma tampil di lebar mobile) ditambahkan ke `absen.html`/`riwayat.html`/`izin.html`: Beranda · Riwayat · Izin · Profil. Halaman **Riwayat Presensi** (`/presensi/riwayat/`) menampilkan gabungan Presensi + IzinCuti disetujui milik sendiri, bulan berjalan. Nav sidebar desktop untuk Presensi/Riwayat/Izin & Cuti diperluas ke **SEMUA role** (bukan cuma dosen lagi), karena halaman-halaman ini sudah generik berbasis `user` (siap dipakai staf juga, bukan tergantung NIDN).

**[KELOMPOK STAF/TENDIK, TARGET JAM KERJA BULANAN, & LEMBUR — selesai per 2026-07-29]** Perluasan dari fitur Kelompok Presensi di atas, atas permintaan user untuk melengkapi laporan presensi sebagai dasar penggajian:
- ✅ **Kelompok "Staf/Tendik"** ditambahkan (migrasi data `0008_seed_kelompok_staf_tendik`) — baris kelompok TERPISAH dari "Pejabat" (bukan digabung), jam kerja sama persis (08.00-16.00 Senin-Sabtu) tapi role `["tendik"]` sendiri. Keputusan user: dipisah supaya jam/target tendik bisa diatur beda dari pejabat nanti tanpa migrasi skema lagi.
- ✅ **Model `TargetKerjaBulanan`** (`presensi/models.py`, migrasi `0007_targetkerjabulanan`) — `kelompok` (FK), `bulan`, `tahun`, `target_hari_kerja`, `target_jam_kerja`. Diisi **MANUAL per bulan+tahun** oleh HR lewat admin (bukan dihitung otomatis dari kalender) — keputusan user, supaya HR bisa atur beda tiap bulan (mis. Ramadan/semester pendek) dan tetap pegang kendali penuh atas angka resmi dasar penggajian.
- ✅ **Status kedatangan/kepulangan granular** — `Presensi` (migrasi `0009_tambah_field_lembur_presensi`) dapat field baru: `menit_lebih_awal`, `menit_terlambat` (dihitung saat masuk), `menit_pulang_cepat`, `menit_lembur` (dihitung saat pulang) — SEMUA selisih murni dari jam kelompok/lokasi, TIDAK memperhitungkan `toleransi_menit` (itu cuma untuk status HADIR/TELAT biner di `tentukan_status_waktu`). Dihitung di `presensi/decision.py::hitung_ketepatan_masuk/pulang`, dipanggil dari `AbsenMasukView`/`AbsenPulangView`. Field `status` (HADIR/TELAT/IZIN/ALPA/DITOLAK) TIDAK diubah/digantikan — field granular ini melengkapi, bukan menggantikan.
- ✅ **Alur lembur & approval** — lembur > `BATAS_MENIT_LEMBUR_WAJIB_KETERANGAN` (120 menit, `presensi/models.py`) WAJIB diisi `keterangan_lembur` sebelum `AbsenPulangView` menerima absen pulang (alasan `keterangan_lembur_wajib` kalau kosong — user harus isi field lalu ulangi, lihat textarea kondisional di `absen.html`); lembur ≤120 menit otomatis diterima tanpa keterangan/approval. Kalau >120 menit & keterangan terisi, `status_lembur` jadi `menunggu` dan tampil di kartu baru "Lembur Menunggu Persetujuan" di `/presensi/tinjau/` (`templates/presensi/tinjau.html`), diputuskan lewat `putuskan_lembur` (`presensi/views.py`, URL `tinjau/<id>/putuskan-lembur/`) — approve/reject pola sama seperti `putuskan_izin`. **Kalau ditolak, `waktu_pulang` ASLI TIDAK diubah** (tetap sesuai realita, prinsip "server adalah otoritas") — yang dibatasi cuma jam kerja TERHITUNG (lihat poin berikut).
- ✅ **`Presensi.durasi_kerja_menit` / `.durasi_kerja`** (properti, `presensi/models.py`) — durasi kerja efektif dalam menit / format "JJ:MM" (`format_jam_menit()`). Kalau `status_lembur` `menunggu` atau `ditolak`, jam pulang efektif yang dipakai untuk hitung durasi dibatasi ke jam pulang normal kelompok/lokasi (jam lembur tidak ikut dihitung sampai disetujui). Ditampilkan per-baris di `/presensi/riwayat/` (`templates/presensi/riwayat.html`).
- ✅ **`presensi/rekap.py::rekap_bulanan_user(user, bulan, tahun)`** — jumlah `durasi_kerja_menit` sebulan (presensi `DITOLAK` dikecualikan) dibandingkan ke `TargetKerjaBulanan` kelompoknya (kelompok diambil dari snapshot presensi bulan itu). Ditampilkan sebagai ringkasan "Total jam kerja bulan ini vs Target" di bagian atas `/presensi/riwayat/`.
- ✅ **Laporan Bulanan Jam Kerja lintas-pegawai SELESAI per 2026-07-29** — `/presensi/laporan-bulanan/` (`templates/presensi/laporan_bulanan.html`) & ekspor Excel `/presensi/laporan-bulanan/ekspor/`, ditaruh di app `presensi` (BUKAN app `laporan` — app itu isinya laporan kinerja riset/publikasi, domain berbeda). **Sengaja LINTAS-PEGAWAI** (dosen + staf/tendik + pejabat via `accounts.User` langsung, BUKAN `get_dosen_queryset` yang dosen-only) — cakupannya di-scope lewat `dapat_kelola`, pola sama dengan `/presensi/tinjau/`. Logika `presensi/rekap.py::laporan_bulanan_jam_kerja(user_qs, bulan, tahun)` — 1 baris per user yang PUNYA presensi di bulan itu (bukan semua user dalam cakupan seperti `data_presensi_harian`), pakai `rekap_bulanan_user` per baris + `selisih_menit`/`selisih_jam_kerja` (format "+JJ:MM"/"-JJ:MM" vs target). Link nav ditambahkan di `templates/base.html` section Administrasi (role sama dengan Tinjau Presensi). Ini menjawab catatan lama soal lokasi laporan rekap bulanan yang "masih belum diputuskan" — sudah diputuskan & dibangun di app `presensi`.
- Test baru: `FormatJamMenitTest`, `HitungKetepatanMasukPulangTest`, `DurasiKerjaPresensiTest`, `SeedKelompokStafTendikTest`, `RekapBulananUserTest`, `PutuskanLemburViewTest`, `LaporanBulananViewTest`, plus kasus lembur di `AbsenPulangAPITest` — **sudah dites & LOLOS di VPS per 2026-07-29 (114/114 test saat itu)**, setelah 2 ronde perbaikan bug test murni (bukan bug aplikasi): (1) `timezone.localdate()` yang dipanggil di dalam body test yang `timezone.now`-nya sudah di-`@patch` ikut mengembalikan `MagicMock` — perbaikannya hitung tanggal SEBELUM patch aktif (di `setUp`); (2) perbandingan `waktu_pulang.time()` setelah `refresh_from_db()` harus lewat `timezone.localtime()` dulu (ORM mengembalikan datetime UTC, bukan waktu lokal WITA yang aslinya di-set); (3) `test_pulang_setelah_masuk_diterima` sempat jadi flaky tergantung jam sungguhan server (bisa kena aturan wajib `keterangan_lembur` kalau kebetulan dites >2 jam lewat jam pulang kelompok) — diperbaiki dengan mem-pin waktu lewat mock, bukan real clock.

**[UI PENGATURAN & PELENGKAP TAMPILAN — selesai per 2026-07-29]** Setelah fitur di atas dibangun, user menanyakan apakah semua pengaturan (kelompok, hari libur, target) sudah punya tampilan di portal atau baru di database/Django Admin saja -- jawabannya saat itu SEBAGIAN (kelompok/hari-libur/target cuma bisa diatur lewat `/admin/`, Dashboard & Data Presensi belum menampilkan kelompok/lembur). Ini semua sudah dilengkapi:
- ✅ **Halaman Pengaturan Presensi** (admin-only, BUKAN di-scope fakultas/prodi seperti Tinjau Presensi — institusi-wide jadi sengaja dibatasi role `admin` saja lewat `_bisa_kelola_pengaturan_presensi`): `/presensi/pengaturan/kelompok/`, `/pengaturan/hari-libur/`, `/pengaturan/target/` (+ form tambah/ubah masing-masing). Kelompok pakai **toggle aktif/nonaktif** (`toggle_aktif_kelompok`), BUKAN hapus — `KelompokPresensi` direferensikan `Presensi.kelompok` dengan `on_delete=PROTECT` jadi tidak boleh dihapus kalau sudah pernah dipakai. `KelompokPresensiForm.roles`/`hari_kerja` pakai checkbox (`CheckboxSelectMultiple`), bukan input teks dipisah koma, supaya HR non-teknis lebih mudah pakainya. Link nav "Pengaturan Presensi" ditambahkan di `templates/base.html` section Administrasi (gated `role == 'admin'`, sama seperti Kelola User/Data Master).
- ✅ **`TargetKerjaBulanan.nama_bulan`** (properti baru, `presensi/models.py`) — pengganti `get_bulan_display()` yang tidak ada karena field `bulan` sengaja `PositiveSmallIntegerField` biasa tanpa `choices` (supaya tidak perlu migrasi kalau nanti mau ganti cara render). `NAMA_BULAN` (list nama bulan Indonesia) juga di `models.py`, dipakai ulang oleh `TargetKerjaBulananForm.bulan` (`forms.py`) supaya tidak duplikasi.
- ✅ **Data Presensi Harian** (`/presensi/data/` + ekspor Excel) — kolom **Kelompok** & **Lembur** (badge menunggu/disetujui/ditolak) ditambahkan, di halaman maupun file Excel-nya (kolom Excel jadi A-J, sebelumnya A-H).
- ✅ **`top_telat_hari_ini`** (`presensi/rekap.py`) — diperbaiki supaya pakai `Presensi.menit_terlambat` yang SUDAH tersimpan (dihitung `hitung_ketepatan_masuk`, kelompok-aware) alih-alih menghitung ulang dari `lokasi.jam_masuk` saja seperti sebelumnya (yang mengabaikan prioritas jam kelompok).
- ✅ **Riwayat Presensi** — label granular "Terlambat N menit" / "Datang N menit lebih awal" / "Pulang N menit lebih cepat" ditambahkan per baris (dari field `menit_terlambat`/`menit_lebih_awal`/`menit_pulang_cepat` yang sebelumnya tersimpan tapi tidak ditampilkan di mana pun).
- Test baru: `PengaturanKelompokViewTest`, `PengaturanHariLiburViewTest`, `PengaturanTargetViewTest`, `TopTelatMenitTerlambatTest` — **sudah dites & LOLOS di VPS (128/128 test)**.

**[LAPORAN DAFTAR HADIR DOSEN SERDOS (LLDIKTI) — selesai per 2026-07-30]** Presensi punya DUA tujuan: internal kampus, dan pelaporan ke LLDIKTI untuk dosen yang lulus Sertifikasi Dosen (Serdos) — laporan resminya ("Daftar Hadir Dosen Tetap Yayasan Penerima Serdos") butuh paraf per hari kerja. User memberi contoh dokumen fisik (foto) sebagai acuan format persis.
- ✅ **Paraf Digital** (`presensi/models.py::ParafDosen`, halaman `/presensi/paraf/`) — dosen gambar paraf SEKALI lewat canvas (Pointer Events API, mouse/jari), disimpan sebagai gambar biasa (bukan biometrik, tidak perlu enkripsi Fernet), lalu **auto-stamp** dipakai berulang ke laporan (keputusan user: sederhana & sesuai permintaan, meski nilai pembuktian sebagai "tanda tangan asli tiap hari" lebih lemah dari kertas — sudah didiskusikan & diterima). Endpoint `POST /api/presensi/paraf`. Link nav khusus role `dosen`.
- ✅ **Cakupan: HANYA dosen serdos DISETUJUI** — `presensi/utils.py::get_dosen_serdos_qs()` filter `profil.Sertifikasi(jenis_sertifikasi='serdos', status_validasi='disetujui')`. Sengaja lebih ketat dari beberapa tempat lain di kode (`profil/views.py::has_serdos` dkk cuma exists() tanpa filter status) — untuk laporan resmi ke lembaga eksternal, cuma yang sudah tervalidasi yang relevan.
- ✅ **Data pendukung SIMDA baru** (`simda_dosen/models.py`, read-only managed=False, pola sama seperti `DataDosen`): `JabatanStruktural` (`master.jabatan_struktural`) & `PejabatStruktural` (`master.pejabat_struktural`, punya `file_ttd`/`lebar_ttd`/`tinggi_ttd` — SIMDA SUDAH punya infrastruktur gambar tanda tangan resmi untuk dokumen PDF). Helper `simda_dosen/utils.py::get_pejabat_aktif(nama_jabatan)` cari pejabat aktif (mis. "Rektor") buat blok tanda tangan otomatis. **PENTING — perlu langkah manual di database SIMDA**: tabel ini belum ada di grant `sikd_rw` (`buat_role_sikd_rw.sql`) — sudah dibuatkan `tambah_akses_pejabat_struktural.sql` (repo SIMDA, `C:\unisan\simda\`, TIDAK masuk repo kinerja-dosen karena beda proyek) dan dikirim ke user untuk dijalankan sendiri di database `unisan_db` lewat pgAdmin/psql. Tanpa grant ini, `get_pejabat_aktif` akan gagal query (permission denied) di produksi.
- ✅ **Urutan Laporan Serdos** (`presensi/models.py::UrutanSerdos`, tab baru "Urutan Laporan Serdos" di Pengaturan Presensi) — urutan baris di laporan resmi mengikuti urutan SK/kepegawaian institusi (BUKAN alfabetis nama/NIDN, sesuai contoh dokumen), yang tidak tersimpan di data mana pun (SIKD maupun SIMDA) — jadi diatur manual admin lewat satu form besar (bukan tambah/ubah satu-satu, supaya HR bisa isi semua dosen serdos sekaligus). Dosen yang belum diatur urutannya ditaruh di akhir daftar, urut nama.
- ✅ **`presensi/laporan_serdos.py::data_laporan_serdos(bulan, tahun)`** — logika inti (dipisah dari `views.py`/`rekap.py`, domainnya beda: kepatuhan LLDIKTI, bukan payroll internal), return list `BarisSerdos` per dosen: grid tanggal (`HariGrid`: kerja/minggu/libur + status hadir), Gol/Jabatan Akademik dirakit dari `GolonganPublik.kode` + `JabatanFungsionalPublik.nama` SIMDA (DataDosen cuma simpan id-nya, bukan teksnya), deteksi "Tugas Belajar" dari `DataDosen.status_kepegawaian_nama` (field ini SUDAH ada di SIMDA, dipetakan otomatis — baris dosen tugas belajar diganti teks "TUGAS BELAJAR / BIAYA PEMERINTAH" merentang, bukan grid paraf).
- ✅ **Ekspor PDF** (`presensi/laporan_serdos_pdf.py`, reportlab — library pertama di project yang menyisipkan GAMBAR ke PDF, sebelumnya cuma tabel teks) — page size A3 landscape (dibutuhkan supaya ±31 kolom tanggal muat), replikasi header (logo+judul+yayasan/PTS/bulan), tabel dengan gambar paraf ditempel per sel, baris Tugas Belajar pakai `SPAN`, kolom Minggu/hari libur diarsir **abu solid** (BUKAN pola diagonal seperti kertas asli — reportlab Table tidak punya hatch-fill bawaan, dan bikin custom canvas draw per sel jauh lebih rumit untuk hasil yang secara fungsi sama), legenda KET, blok tanda tangan (gambar TTD dari SIMDA + nama digarisbawahi + NIP).
- ✅ **Ekspor Excel** (`presensi/laporan_serdos_excel.py`, openpyxl) — versi sama persis, gambar ditempel pakai `openpyxl.drawing.image.Image` (catatan: nempel sebagai overlay ke sel, BUKAN "fit di dalam" sel seperti reportlab Table cell — keterbatasan openpyxl yang sudah diketahui, bukan bug).
- ✅ **Halaman `/presensi/laporan-serdos/`** (admin-only) — form bulan/tahun/kota/tanggal cetak/jabatan+nama+NIP penandatangan (nama/NIP/gambar TTD **otomatis** dari `get_pejabat_aktif` kalau field dikosongkan, tapi tetap bisa diedit manual — mis. kalau mau ditandatangani pejabat lain). Tanggal cetak default = tanggal 1 bulan BERIKUTNYA (pola dari contoh dokumen: laporan bulan berjalan ditandatangani awal bulan depan). Satu form, dua tombol unduh (PDF/Excel) pakai `formaction` HTML — bukan dua form terpisah.
- Test baru: `GetDosenSerdosQsTest`, `JenisTanggalBulanTest`, `DataLaporanSerdosTest`, `GetPejabatAktifTest`, `PengaturanUrutanSerdosViewTest`, `LaporanSerdosViewTest` — SIMDA di-mock (pola sama dengan `GetDosenByNidnTest`, database `simda` tidak selalu tersedia saat test).
- ⚠️ **Bug ditemukan & diperbaiki setelah deploy pertama**: `get_pejabat_aktif` belum membungkus query `master.pejabat_struktural` dengan penanganan error — sebelum user sempat menjalankan `tambah_akses_pejabat_struktural.sql` di SIMDA, `ProgrammingError: permission denied for table pejabat_struktural` bikin **seluruh** halaman `/presensi/laporan-serdos/` 500 (bukan cuma field nama/NIP kosong seperti yang diklaim sebelumnya). Diperbaiki dengan `try/except DatabaseError: return None` di `simda_dosen/utils.py::get_pejabat_aktif` — aman ditangkap tanpa rollback manual karena koneksi `'simda'` jalan di mode autocommit (tidak ada `ATOMIC_REQUESTS` di settings). Test regresi: `GetPejabatAktifTest::test_permission_denied_mengembalikan_none_bukan_crash`.

**[LAPORAN PRESENSI INTERNAL — selesai per 2026-07-31]** Beda dari Laporan Daftar Hadir Serdos (format resmi LLDIKTI, dosen serdos saja, ada paraf): ini laporan bulanan **internal kampus**, lintas-pegawai (dosen+pejabat+tendik), tanpa paraf — isinya jam Masuk/Pulang harian. Bisa difilter kategori pegawai, fakultas, program studi.
- ✅ **Kategori — cuma 2: "Dosen" (termasuk Pejabat Struktural) & "Tendik"** — `presensi/laporan_internal.py::KATEGORI_ROLES` = `{"dosen": ["dosen","dekan","wadek","kaprodi","sekprodi","rektorat","biro"], "tendik": ["tendik"]}`. **Keputusan per 2026-07-31** (user awalnya tanya apakah jam kerja presensi Dosen & Pejabat sebaiknya disatukan — dianalisis & diputuskan TIDAK, KelompokPresensi/jam kerja gerbang presensi & Target Kerja Bulanan tetap terpisah seperti semula karena pejabat struktural punya kebutuhan jam kantor lebih panjang untuk tugas administratif; yang digabung CUMA kategori tampilan di laporan ini, karena secara kepegawaian pejabat struktural tetap dosen). Kategori "Pejabat" terpisah yang sempat ada di versi awal (per 2026-07-31 pagi) sudah dihapus. Role `admin`/`operator` sengaja tidak masuk kategori manapun (konsisten dengan seed `KelompokPresensi`) — tetap muncul kalau filter kategori dikosongkan.
- ✅ **Program Studi** — `master.models.Prodi` (BUKAN `simda_dosen.ProdiPublik`/SIMDA — itu untuk keperluan lain, dropdown Mata Kuliah/Mahasiswa). `accounts.User.kode_prodi` cuma CharField kode, jadi nama diambil lewat map `{kode_prodi: nama_prodi}` sekali query (bukan N+1 per user).
- ✅ **Kolom Masuk/Pulang ditumpuk 1 kolom per tanggal** (BUKAN 2 kolom terpisah seperti diminta awalnya) — setelah dianalisis, 2 kolom/tanggal x ±31 hari = ±62 kolom butuh lebar ±43-45cm (lebih lebar dari A3/42cm, apalagi F4/33cm yang diminta user). User pilih opsi ditumpuk (1 kolom/tanggal, teks 2 baris "08:05"/"14:12") supaya tetap muat di F4 landscape — jumlah kolom jadi sama seperti Laporan Serdos (~31).
- ✅ **Ekspor PDF** (`presensi/laporan_internal_pdf.py`, reportlab, **F4 landscape** — beda dari Serdos yang A3, karena di sini cuma teks bertumpuk bukan gambar paraf jadi jauh lebih hemat lebar) & **Excel** (`presensi/laporan_internal_excel.py`, openpyxl) — TANPA paraf/tugas-belajar/blok tanda tangan (laporan internal, bukan dokumen resmi eksternal).
- ✅ **Halaman `/presensi/laporan-internal/`** — akses **scoped `dapat_kelola`** (BUKAN admin-only seperti Pengaturan/Serdos) — sama seperti Laporan Bulanan Jam Kerja, karena ini tools operasional harian, bukan pengaturan institusi-wide. Dropdown Fakultas/Prodi diisi dinamis dari `master.Fakultas`/`master.Prodi` di `LaporanInternalForm.__init__` (query saat request, bukan saat modul di-import).
- Tidak ada model/migrasi baru — laporan ini murni membaca data yang sudah ada (`Presensi`, `accounts.User`, `master.Prodi`/`Fakultas`).
- Test baru: `GetUserQsLaporanInternalTest`, `DataLaporanInternalTest`, `LaporanInternalViewTest` — SEMUA data lokal (tidak ada SIMDA di sini), jadi tidak perlu mock seperti test-test Serdos — **belum dites di VPS**, perlu dijalankan setelah deploy.

**[DETAIL PRESENSI BULANAN — selesai per 2026-07-31]** Fitur opsional drill-down: lihat rincian presensi SATU orang per hari dalam SATU bulan (dicari lewat nama/username/NIDN), dipakai kalau perlu mengecek riwayat kehadiran seseorang secara spesifik — beda dari 3 laporan lain yang semuanya rekap banyak-orang/1-bulan atau diri-sendiri/bulan-berjalan.
- ✅ **Alur pencarian** (`AskUserQuestion`, user pilih "Tampilkan daftar, pilih salah satu") — `presensi/laporan_detail.py::cari_pegawai(user_qs, kata_kunci)` filter `Q` di `first_name`/`last_name`/`username`/`nidn`. 0 hasil → pesan "tidak ditemukan", 1 hasil → langsung tampil detail, >1 hasil → tabel pilihan dengan link "Lihat Detail" (`?user_id=`).
- ✅ **`detail_presensi_bulanan(user, bulan, tahun)`** — 1 baris per tanggal (pakai `jenis_tanggal_bulan` dari `laporan_serdos.py`, dipakai ulang lintas-laporan), gabung data `Presensi` (status/jam masuk-pulang/keterangan granular telat-pulang cepat-lembur dari field `menit_*` yang sudah ada) dan `IzinCuti` disetujui (fallback kalau tidak ada presensi hari itu) — hari kerja tanpa presensi maupun izin ditandai "Alpa", hari libur/minggu tanpa presensi ditandai "Libur". Rekap total jam kerja/target/selisih pakai `rekap_bulanan_user()` yang sudah ada (`presensi/rekap.py`), tidak ada logika baru untuk itu.
- ✅ **Ekspor PDF** (`presensi/laporan_detail_pdf.py`, reportlab, **A4 portrait** — beda dari 3 laporan lain yang landscape lebar, karena di sini cuma ±31 baris tanggal untuk 1 orang, bukan grid banyak-orang) & **Excel** (`presensi/laporan_detail_excel.py`, openpyxl) — user eksplisit minta opsi unduh juga (bukan cuma tampilan layar).
- ✅ **Halaman `/presensi/laporan-detail/`** — akses **scoped `dapat_kelola`** (BUKAN admin-only), pola sama seperti Laporan Bulanan/Internal karena tools operasional harian. Link cross-referensi "Lihat Detail" ditambahkan di baris tabel `/presensi/laporan-bulanan/` supaya gampang loncat dari rekap-banyak-orang ke detail-satu-orang. Nav sidebar "Detail Presensi Bulanan" ditambahkan di section yang sama dengan Laporan Bulanan/Internal.
- **Keputusan lokasi fitur** (dianalisis sesuai permintaan user "cocok digabung dimana"): dibuat halaman baru sendiri, bukan digabung ke salah satu dari 3 laporan yang sudah ada — karena bentuk interaksinya beda (cari-1-orang+bulan-bebas vs daftar-banyak-orang+1-bulan vs diri-sendiri+bulan-berjalan), tapi logika inti (`rekap_bulanan_user`, `jenis_tanggal_bulan`) dipakai ulang penuh, bukan ditulis ulang.
- Tidak ada model/migrasi baru — murni membaca data yang sudah ada (`Presensi`, `IzinCuti`, `accounts.User`).
- Test baru: `CariPegawaiTest`, `DetailPresensiBulananTest`, `LaporanDetailViewTest` — **belum dites di VPS**, perlu dijalankan setelah deploy.
