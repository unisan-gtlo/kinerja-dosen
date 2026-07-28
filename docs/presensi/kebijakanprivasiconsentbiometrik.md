# Kebijakan Privasi & Formulir Persetujuan Data Biometrik
### Modul Presensi — Portal Kinerja UNISAN

> **Template awal.** Tinjau bersama bagian hukum/kepegawaian dan sesuaikan dengan
> kebijakan resmi UNISAN sebelum dipakai. Dokumen ini mengacu pada **UU No. 27 Tahun 2022
> tentang Pelindungan Data Pribadi (UU PDP)**, yang menggolongkan data wajah/biometrik
> sebagai **data pribadi bersifat spesifik**.

---

## 1. Tujuan Pengumpulan Data
Universitas mengumpulkan dan memproses data wajah dosen/pegawai semata-mata untuk
**verifikasi kehadiran (presensi)** — memastikan absensi dilakukan oleh orang yang
bersangkutan dan di lokasi kerja. Data tidak digunakan untuk tujuan lain.

## 2. Data yang Dikumpulkan
- **Wajah:** disimpan sebagai *embedding* (representasi angka) **terenkripsi**, bukan
  foto mentah, bila memungkinkan.
- **Foto selfie saat absen:** sebagai bukti, dengan masa simpan terbatas.
- **Lokasi (GPS)** dan **informasi perangkat** saat presensi.

## 3. Dasar Pemrosesan
Pemrosesan dilakukan berdasarkan **persetujuan (consent)** yang diberikan secara sadar,
serta dalam rangka pelaksanaan kewajiban kepegawaian.

## 4. Penyimpanan & Keamanan
- Embedding wajah **dienkripsi** saat disimpan (*at rest*) dan dikirim melalui **HTTPS**.
- Akses data biometrik **dibatasi** hanya untuk peran tertentu (HR/IT) dan **dicatat** (audit).
- Foto bukti disimpan maksimal **[isi: mis. 90 hari]**, lalu dihapus otomatis.

## 5. Hak Dosen/Pegawai
Sesuai UU PDP, subjek data berhak untuk: mengakses datanya, meminta perbaikan,
**menarik persetujuan**, dan meminta **penghapusan** data biometriknya.

## 6. Metode Alternatif (Non-Biometrik)
Bagi yang **tidak bersedia** memberikan data wajah, universitas menyediakan metode
presensi alternatif **[isi: mis. QR + PIN / verifikasi manual oleh atasan]**, sehingga
tidak ada pegawai yang dirugikan karena menolak biometrik.

## 7. Retensi & Penghapusan
Data biometrik dihapus bila: pegawai berhenti/pensiun, menarik persetujuan, atau setelah
melewati masa retensi yang ditetapkan.

---

## FORMULIR PERSETUJUAN (CONTOH)

Saya yang bertanda tangan di bawah ini:

- Nama : ____________________________
- NIDN : ____________________________
- Unit/Fakultas : ____________________

Dengan ini menyatakan bahwa saya telah membaca dan memahami kebijakan di atas, dan:

☐ **SETUJU** data wajah saya dikumpulkan dan diproses untuk keperluan presensi.
☐ **TIDAK SETUJU**, dan memilih metode presensi alternatif yang disediakan.

Tanda tangan : ____________________     Tanggal : ______________

> Catatan teknis: status persetujuan ini direkam di sistem pada field
> `EnrolmentWajah.consent_disetujui` beserta `consent_pada` (waktu server).
