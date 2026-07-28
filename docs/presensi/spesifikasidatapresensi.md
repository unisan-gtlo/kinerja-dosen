# Spesifikasi Data — Modul Presensi (Portal Kinerja UNISAN)

Versi 1.1 · basis PostgreSQL biasa (tanpa PostGIS/GDAL — lihat catatan di bawah).
Semua tabel berada di app Django `presensi`.

## Prinsip relasi dosen
- **Data dosen tidak diduplikasi.** Setiap tabel yang butuh dosen menyimpan field
  **`nidn`** (`CharField` biasa, BUKAN `ForeignKey`), dicocokkan ke model dosen di
  app **`simda_dosen`** (model `DataDosen`, field `nidn`).
- **Kenapa bukan `ForeignKey`:** tabel `simda_dosen.DataDosen` fisiknya ada di
  database Postgres terpisah (`unisan_db`, koneksi alias `simda`), sedangkan tabel
  presensi ada di `sikd_db` (koneksi `default`). Postgres tidak mendukung FK/JOIN
  lintas database, dan `config/db_router.py::SimdaRouter.allow_relation()` memang
  sengaja melarang relasi lintas-app ke `simda_dosen`. Resolusi dilakukan manual di
  kode lewat `presensi.utils.get_dosen_by_nidn(nidn)` — pola yang sama sudah dipakai
  app `profil` (lihat `simda_dosen/utils.py::get_simda_dosen_or_none`).
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
| nidn | varchar(20), blank | Jadwal khusus dosen; kosong = pakai default lokasi |
| lokasi | FK → LokasiKantor | |
| hari | smallint | 0=Senin .. 6=Minggu |
| jam_masuk / jam_pulang | time | |

### Perangkat (device binding)
| Field | Tipe | Keterangan |
|---|---|---|
| nidn | varchar(20) | |
| device_id | varchar(200) | ID unik perangkat |
| platform | varchar | android/ios/web |
| terpercaya | bool | Disetujui admin |
| is_rooted | bool | Terdeteksi root/emulator |
| terakhir_dipakai | datetime | |
| *unik* | (nidn, device_id) | |

### EnrolmentWajah (biometrik)
| Field | Tipe | Keterangan |
|---|---|---|
| nidn | varchar(20), unik | |
| embedding_terenkripsi | binary | **Embedding terenkripsi**, bukan foto mentah |
| versi_model | varchar | mis. arcface-r100 |
| consent_disetujui | bool | Persetujuan biometrik (UU PDP) |
| consent_pada | datetime | |

### Presensi (inti)
| Field | Tipe | Keterangan |
|---|---|---|
| nidn | varchar(20) | |
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
| *unik* | (nidn, tanggal) | |

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
| nidn | varchar(20) | |
| tipe | enum | izin / sakit / cuti / dinas |
| tanggal_mulai / tanggal_selesai | date | |
| alasan | text | |
| lampiran | file | |
| status | enum | menunggu / disetujui / ditolak |
| approver | varchar | NIDN/ID atasan |

### LogKecurangan (audit anti-fraud)
| Field | Tipe | Keterangan |
|---|---|---|
| nidn | varchar(20) | |
| presensi | FK → Presensi (nullable) | |
| jenis_anomali | varchar | mis. mock_location, wajah_tidak_cocok |
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
