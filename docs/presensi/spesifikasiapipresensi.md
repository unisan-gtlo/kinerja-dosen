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

Request (multipart): `foto` (2–5 gambar), `consent` (bool, wajib true).
Response sukses: `{ "status": "ok", "versi_model": "insightface-buffalo_l", "consent_pada": "..." }`
Response gagal (400): `{ "status": "gagal", "alasan": "nidn_tidak_terdaftar | wajah_tidak_terdeteksi_konsisten" }`

Catatan implementasi (lihat `presensi/face.py`, `presensi/views.py::EnrolmentWajahView`):
- Model: **InsightFace/ArcFace (`buffalo_l`)**, jalan di CPU. Embedding rata-rata
  dari semua foto yang berhasil terdeteksi (minimal 2), disimpan **terenkripsi**
  (Fernet, kunci `FIELD_ENCRYPTION_KEY`).
- **Diproses sinkron** (bukan Celery/Redis) untuk sekarang -- enrolment jarang
  dilakukan (sekali per dosen) dan skala kecil (~150 dosen), jadi latensi
  beberapa detik per request dianggap wajar. Revisit ke Celery kalau ternyata
  jadi masalah nyata.

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

**Catatan JUJUR soal liveness (per implementasi saat ini):** pemeriksaan
`liveness_gagal` BARU heuristik sederhana (persis 1 wajah terdeteksi, skor
deteksi cukup tinggi, ukuran wajah wajar dalam bingkai) -- **BUKAN** anti-spoof
sungguhan, belum bisa membedakan foto cetak/replay video dari wajah asli.
Lihat `presensi/face.py` untuk detail & catatan upgrade ke model anti-spoof
kalau dibutuhkan nanti.

Gerbang lolos (`diterima: true`) sekarang otomatis `tingkat_risiko: "rendah"`
(`ditandai: false`) -- tidak lagi butuh tinjauan HR manual seperti saat syarat
wajah belum aktif.

### POST `/api/presensi/pulang`
Sama seperti masuk (mencatat `waktu_pulang`).

### GET `/api/presensi/status-hari-ini`
Status presensi dosen untuk hari berjalan (untuk layar beranda).

### GET `/api/presensi/riwayat?bulan=YYYY-MM`
Riwayat presensi pribadi + rekap. **[Belum diimplementasikan]**

---

## Izin & Cuti
| Method | Path | Keterangan |
|---|---|---|
| POST | `/api/presensi/izin` | Ajukan izin/cuti/dinas (+lampiran) |
| GET | `/api/presensi/izin` | Daftar & status pengajuan pribadi |
| POST | `/api/presensi/izin/{id}/approval` | Atasan menyetujui/menolak (role terbatas) |

---

## Admin / HR (role terbatas)
**Sudah diimplementasikan sebagai halaman web** (bukan API JSON di bawah ini):
`/presensi/tinjau/` (lihat `templates/presensi/tinjau.html`) -- daftar presensi
`ditandai=True`, tombol Setujui/Tolak. Dibatasi role admin +
dekan/wadek/kaprodi/sekprodi/operator, di-scope per fakultas/prodi.

**Catatan penting sejak gerbang-DAN penuh aktif (lokasi + wajah):** presensi
yang lolos KEDUA syarat otomatis `tingkat_risiko: rendah` + `ditandai: false`
(tidak perlu tinjauan HR); yang gagal salah satu syarat langsung **ditolak**
(tidak pernah membuat baris Presensi, cuma tercatat di `LogKecurangan`). Efeknya,
antrian `/presensi/tinjau/` sekarang jarang/tidak terisi lagi untuk presensi
baru. Kalau ke depannya dibutuhkan nuansa tambahan (mis. skor kemiripan wajah
yang pas-pasan di atas ambang tetap ditandai untuk ditinjau, bukan langsung
disahkan penuh), itu perbaikan lanjutan di `presensi/decision.py`/`views.py`,
belum diterapkan saat ini.

Endpoint JSON berikut **BELUM diimplementasikan** (spec awal, referensi untuk
pengembangan lanjutan):

| Method | Path | Keterangan |
|---|---|---|
| GET | `/api/presensi/admin/dashboard` | KPI kehadiran hari ini |
| GET | `/api/presensi/admin/data?tanggal=&unit=` | Data presensi + filter |
| GET | `/api/presensi/admin/ekspor?format=xlsx\|pdf` | Ekspor laporan |
| CRUD | `/api/presensi/admin/lokasi` | Kelola LokasiKantor & geofence + flag opsi (sudah bisa lewat Django admin: `/admin/presensi/lokasikantor/`) |

---

## QR dinamis (opsi, bila diaktifkan)
| Method | Path | Keterangan |
|---|---|---|
| GET | `/api/presensi/qr/{lokasi_id}` | Ambil token QR aktif (untuk layar/tablet di pintu); berganti ±60 dtk |

---

## Kode alasan penolakan (untuk UI & LogKecurangan)
**Sudah diimplementasikan:** `di_luar_radius`, `akurasi_buruk`, `liveness_gagal`,
`wajah_tidak_cocok` (empat ini dicatat ke `LogKecurangan`), `belum_enrolment_wajah`
& `foto_tidak_valid` (ditolak, TAPI sengaja tidak dicatat sebagai kecurangan --
itu soal kesiapan data, bukan indikasi curang), `nidn_tidak_terdaftar`,
`sudah_absen_masuk`, `sudah_absen_pulang`, `belum_absen_masuk`.

**Belum diimplementasikan** (spec awal, menyusul bersama opsi QR/Wi-Fi):
`mock_location`, `qr_kedaluwarsa`, `perangkat_tidak_dikenal`, `di_luar_jam`.
