# Spesifikasi API — Modul Presensi (Portal Kinerja UNISAN)

Versi 1.1 · Django REST Framework. Semua endpoint:
- **Wajib autentikasi** — JWT (klien mobile/PWA) atau sesi Django (halaman web
  `/presensi/`, lihat catatan di bawah) — kecuali login.
- **Divalidasi & diputuskan di server** (klien hanya kirim data mentah).
- Kena **rate-limiting** (6x/menit per user, scope `presensi`). Waktu memakai
  **jam server**.

Base URL API: `/api/presensi/`

**Halaman web:** `/presensi/` — tombol Absen Masuk/Pulang untuk dosen yang
sudah login di portal (Tabler UI + JS geolocation, lihat
`templates/presensi/absen.html`). Memanggil API yang sama lewat sesi Django
(`SessionAuthentication`), bukan token JWT — JWT tetap dipakai khusus untuk
klien mobile terpisah (lihat status MVP di CLAUDE.md § 9).

---

## Autentikasi
| Method | Path | Keterangan |
|---|---|---|
| POST | `/api/auth/login` | Login pakai akun portal kinerja → kembalikan JWT (access & refresh) |
| POST | `/api/auth/refresh` | Perbarui access token |

---

## Enrolment wajah (sekali di awal)
### POST `/api/presensi/enrolment-wajah`
Kirim beberapa foto untuk didaftarkan sebagai embedding.

Request (multipart): `foto[]` (2–5 gambar), `consent` (bool, wajib true).
Response: `{ "status": "ok", "versi_model": "...", "consent_pada": "..." }`
Catatan: proses embedding dijalankan asinkron (Celery); embedding disimpan terenkripsi.

---

## Presensi (inti — 2 syarat)
### POST `/api/presensi/masuk`
Absen masuk. Server memvalidasi **lokasi (geofence)** DAN **wajah (match + liveness)**.

Request (multipart):
```
lat            float   (wajib)
lng            float   (wajib)
akurasi_m      float   (wajib)
selfie         file    (wajib)
device_id      string  (wajib)
qr_token       string  (opsional; bila lokasi.wajib_qr)
ssid / ip      string  (opsional; bila lokasi.wajib_wifi)
```
Response (200):
```json
{
  "diterima": true,
  "status": "hadir",
  "waktu_masuk": "2026-07-25T08:02:11+08:00",
  "lokasi": "Kampus Utama",
  "skor_risiko": 8,
  "tingkat_risiko": "rendah"
}
```
Response gagal (200 dengan diterima=false, atau 4xx):
```json
{
  "diterima": false,
  "alasan": "di_luar_radius | wajah_tidak_cocok | liveness_gagal | akurasi_buruk | qr_kedaluwarsa",
  "tingkat_risiko": "tinggi"
}
```
Aturan keputusan: diterima **hanya jika** lokasi di dalam geofence **DAN** wajah cocok + liveness lolos (gerbang DAN). Opsi QR/Wi-Fi jadi sinyal tambahan bila diaktifkan.

### POST `/api/presensi/pulang`
Sama seperti masuk (mencatat `waktu_pulang`).

### GET `/api/presensi/status-hari-ini`
Status presensi dosen untuk hari berjalan (untuk layar beranda).

### GET `/api/presensi/riwayat?bulan=YYYY-MM`
Riwayat presensi pribadi + rekap.

---

## Izin & Cuti
| Method | Path | Keterangan |
|---|---|---|
| POST | `/api/presensi/izin` | Ajukan izin/cuti/dinas (+lampiran) |
| GET | `/api/presensi/izin` | Daftar & status pengajuan pribadi |
| POST | `/api/presensi/izin/{id}/approval` | Atasan menyetujui/menolak (role terbatas) |

---

## Admin / HR (role terbatas)
| Method | Path | Keterangan |
|---|---|---|
| GET | `/api/presensi/admin/dashboard` | KPI kehadiran hari ini |
| GET | `/api/presensi/admin/data?tanggal=&unit=` | Data presensi + filter |
| GET | `/api/presensi/admin/ditandai` | Presensi berisiko untuk ditinjau |
| POST | `/api/presensi/admin/ditandai/{id}/putuskan` | Setujui/tolak hasil tinjauan |
| GET | `/api/presensi/admin/ekspor?format=xlsx\|pdf` | Ekspor laporan |
| CRUD | `/api/presensi/admin/lokasi` | Kelola LokasiKantor & geofence + flag opsi |

---

## QR dinamis (opsi, bila diaktifkan)
| Method | Path | Keterangan |
|---|---|---|
| GET | `/api/presensi/qr/{lokasi_id}` | Ambil token QR aktif (untuk layar/tablet di pintu); berganti ±60 dtk |

---

## Kode alasan penolakan (untuk UI & LogKecurangan)
`di_luar_radius`, `akurasi_buruk`, `mock_location`, `wajah_tidak_cocok`,
`liveness_gagal`, `qr_kedaluwarsa`, `perangkat_tidak_dikenal`, `di_luar_jam`.
