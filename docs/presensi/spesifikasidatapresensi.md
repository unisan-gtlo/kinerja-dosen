# Spesifikasi Data — Modul Presensi (Portal Kinerja UNISAN)

Versi 1.2 · basis PostgreSQL biasa (tanpa PostGIS/GDAL — lihat catatan di bawah).
Semua tabel berada di app Django `presensi`.

## Prinsip relasi identitas (dosen & staf)
- **Kunci identitas presensi adalah `user`** (`ForeignKey` ke `accounts.User`,
  BUKAN `nidn` lagi) — supaya presensi berlaku untuk **dosen maupun staf/tendik**
  (staf tidak punya NIDN). `accounts.User` ada di database yang SAMA (`sikd_db`)
  dengan presensi, jadi FK biasa aman dipakai (beda dengan data dosen di
  `simda_dosen`, lihat poin berikutnya).
- **Data dosen tetap tidak diduplikasi.** Untuk mengayakan data dosen (nama
  lengkap+gelar, fakultas/prodi versi SIMDA, dst), ambil NIDN dosen lewat
  `user.nidn` (field yang sudah ada di `accounts.User`), lalu panggil
  `presensi.utils.get_dosen_by_nidn(user.nidn)` untuk resolve ke
  `simda_dosen.DataDosen` — pola yang sama dipakai app `profil` (lihat
  `simda_dosen/utils.py::get_simda_dosen_or_none`). Staf tidak punya NIDN,
  cukup pakai field `accounts.User` langsung (nama, kode_fakultas, kode_prodi
  sudah ada untuk semua role).
- **Kenapa bukan `ForeignKey` langsung ke `simda_dosen.DataDosen`:** tabel itu
  fisiknya ada di database Postgres terpisah (`unisan_db`, koneksi alias
  `simda`). Postgres tidak mendukung FK/JOIN lintas database, dan
  `config/db_router.py::SimdaRouter.allow_relation()` memang sengaja melarang
  relasi lintas-app ke `simda_dosen`. Ini alasan kenapa presensi mereferensikan
  dosen lewat NIDN (via `accounts.User.nidn`), bukan FK langsung ke SIMDA.
- Presensi hanya **membaca** data dosen (read-only).

---

## Tabel

### LokasiKantor
Titik kantor/kampus + geofence. Mendukung banyak lokasi.

| Field | Tipe | Keterangan |
|---|---|---|
| id | PK | |
| nama | varchar(150) | Nama lokasi |
| titik_pusat | PointField (geography) | Koordinat pusat (long/lat) |
| radius_meter | int | Radius geofence (default 100) |
| jam_masuk / jam_pulang | time | Jam kerja default |
| toleransi_menit | int | Batas telat (default 15) |
| timezone | varchar | Default `Asia/Makassar` |
| wajib_qr | bool | **Opsi** — aktifkan verifikasi QR (default false) |
| wajib_wifi | bool | **Opsi** — aktifkan cek Wi-Fi/IP (default false) |
| ssid_wifi / ip_jaringan | varchar | SSID / rentang IP kantor (opsi) |
| aktif | bool | |

### JadwalKerja
| Field | Tipe | Keterangan |
|---|---|---|
| user | FK → accounts.User, nullable | Jadwal khusus orang ini; kosong = pakai default lokasi |
| lokasi | FK → LokasiKantor | |
| hari | smallint | 0=Senin .. 6=Minggu |
| jam_masuk / jam_pulang | time | |

### Perangkat (device binding)
| Field | Tipe | Keterangan |
|---|---|---|
| user | FK → accounts.User | |
| device_id | varchar(200) | ID unik perangkat |
| platform | varchar | android/ios/web |
| terpercaya | bool | Disetujui admin |
| is_rooted | bool | Terdeteksi root/emulator |
| terakhir_dipakai | datetime | |
| *unik* | (user, device_id) | |

### EnrolmentWajah (biometrik)
| Field | Tipe | Keterangan |
|---|---|---|
| user | OneToOne → accounts.User | |
| embedding_terenkripsi | binary | **Embedding terenkripsi**, bukan foto mentah |
| versi_model | varchar | mis. insightface-buffalo_l |
| consent_disetujui | bool | Persetujuan biometrik (UU PDP) |
| consent_pada | datetime | |

### Presensi (inti)
| Field | Tipe | Keterangan |
|---|---|---|
| user | FK → accounts.User | |
| tanggal | date | |
| waktu_masuk / waktu_pulang | datetime | **Selalu waktu server** |
| lokasi | FK → LokasiKantor | |
| latitude_masuk / longitude_masuk | float | Koordinat saat absen masuk |
| latitude_pulang / longitude_pulang | float | Koordinat saat absen pulang |
| akurasi_masuk_m | float | Akurasi GPS (meter) |
| status | enum | hadir / telat / izin / alpa / ditolak |
| skor_risiko | int (0–100) | Hasil mesin skoring |
| tingkat_risiko | enum | rendah / sedang / tinggi |
| ditandai | bool | Perlu tinjauan HR |
| *unik* | (user, tanggal) | |

### FotoPresensi (bukti)
| Field | Tipe | Keterangan |
|---|---|---|
| presensi | FK → Presensi | |
| tipe | enum | masuk / pulang |
| berkas | file | Selfie (retensi terbatas, terenkripsi) |
| face_match_score | float 0–1 | Skor kecocokan wajah |
| liveness_score | float 0–1 | Skor keaslian |
| verified | bool | |

### QRToken (opsi)
| Field | Tipe | Keterangan |
|---|---|---|
| lokasi | FK → LokasiKantor | |
| kode | varchar unik | Token acak |
| kedaluwarsa | datetime | Umur pendek (±60 dtk) |
| dipakai | bool | Sekali pakai |

### IzinCuti
| Field | Tipe | Keterangan |
|---|---|---|
| user | FK → accounts.User | |
| tipe | enum | izin / sakit / cuti / dinas |
| tanggal_mulai / tanggal_selesai | date | |
| alasan | text | |
| lampiran | file | |
| status | enum | menunggu / disetujui / ditolak |
| approver | FK → accounts.User, nullable | Atasan yang menyetujui/menolak |

### LogKecurangan (audit anti-fraud)
| Field | Tipe | Keterangan |
|---|---|---|
| user | FK → accounts.User | |
| presensi | FK → Presensi (nullable) | |
| jenis_anomali | varchar | mis. di_luar_radius, wajah_tidak_cocok, liveness_gagal |
| detail | JSON | Data pendukung |
| skor | int | |
| waktu | datetime | |

---

## Catatan implementasi
- **Tidak memakai PostGIS/GDAL** — GDAL native library tidak tersedia di
  lingkungan dev proyek ini, dan `django.contrib.gis` butuh GDAL hanya untuk
  diimpor. Koordinat disimpan sebagai `latitude`/`longitude` (`FloatField`)
  biasa, cukup untuk skala geofence ratusan meter.
- Jarak ke `LokasiKantor` dihitung dengan formula **Haversine** (lihat
  `presensi/geo.py::jarak_meter` & `dalam_radius`), dibandingkan dengan
  `radius_meter`.
- Enkripsi `embedding_terenkripsi` dengan kunci di env (`FIELD_ENCRYPTION_KEY`).
- Bila di kemudian hari PostGIS/GDAL sudah tersedia di semua lingkungan
  (dev + deploy) dan dibutuhkan query spasial yang lebih kompleks, migrasi ke
  `PointField` bisa dipertimbangkan — tapi ini bukan prasyarat untuk MVP.
