# 🎵 TikTok Analytics Studio (GUI Tkinter)

Aplikasi desktop berbasis Python & Tkinter untuk menganalisis performa akun TikTok:
1. **Mengecek Frekuensi Unggah**: Menganalisis konsistensi jeda antar video, rata-rata hari per unggahan, serta grafik distribusi hari posting terpopuler (Senin - Minggu).
2. **Rata-rata View 10 Video Terakhir**: Menghitung rata-rata tayangan (*average views*), total views, video tertinggi (*peak*), video terendah, dan menampilkan grafik batang interaktif dengan garis benchmark rata-rata.

---

## 🚀 Fitur Utama

- **Modern Dark UI**: Tampilan modern bernuansa TikTok dark theme (`#121217`, aksen TikTok Pink `#FE2C55` & Cyan `#25F4EE`).
- **Kartu Metrik Utama (Quick Stats)**:
  - ⭐ **Rata-rata View (Dinamis sesuai jumlah sampel: 5, 10, 15, 20, 30, dst.)**
  - 📅 **Frekuensi Unggah** (contoh: *~2.3 hari sekali* atau *~3 video / minggu*)
  - 🏆 **View Tertinggi (Peak Video)**
  - 👥 **Total Followers & Suka Akun**
- **Grafik Interaktif (Matplotlib)**:
  - **Tab 1: Grafik Views Video Terakhir**: Menampilkan jumlah view per video sesuai jumlah yang dipilih beserta garis putus-putus rata-rata view (benchmark). Dilengkapi label angka ringkas (K, M, B).
  - **Tab 2: Grafik Frekuensi Unggah**:
    - *Subplot Kiri*: Grafik garis konsistensi jeda waktu (hari) antar unggahan video.
    - *Subplot Kanan*: Diagram batang hari apa yang paling sering digunakan untuk mengunggah video.
- **Tabel Detail Video Lengkap**: Menampilkan informasi setiap video secara detail:
  - `#` (Urutan)
  - `📅 Tanggal Unggah` (Format: `DD/MM/YYYY`)
  - `⏰ Jam Posting` (Format jam menit detik, misal `18:45:10 WIB`)
  - `⏱️ Durasi Video` (Format menit:detik & detik, misal `01:15 (75s)` atau `45s`)
  - `📝 Judul / Caption Video`
  - `👁️ Views (Tayangan)`
  - `❤️ Likes (Suka)`
  - `💬 Komentar`
  - `🔗 Link URL Video` (Klik ganda untuk membuka langsung di browser TikTok)
- **Visualisasi Jam Posting & Durasi**:
  - **Grafik Views**: Menampilkan tanggal, jam posting, dan durasi di label setiap video.
  - **Grafik Frekuensi Unggah (3 Subplot)**:
    1. Konsistensi jeda hari antar unggahan video.
    2. Distribusi hari unggah (Senin - Minggu).
    3. Distribusi waktu jam posting (Pagi, Siang, Sore, Malam, Dini Hari).
- **Analisis Waktu Posting & Durasi**: Di tab *Ringkasan Analitik*, disajikan jam upload paling sering, sesi waktu unggah favorit, rata-rata durasi video, video terpanjang/terpendek, serta karakteristik format konten.
- **Export Data ke CSV**: Kolom ekspor otomatis mencakup tanggal, jam posting, dan durasi video.
- **Export Data ke CSV**: Menyimpan daftar 10 video beserta statistik lengkap ke file spreadsheet CSV.
- **Ringkasan Analitik & Insight**: Laporan otomatis tingkat konsistensi akun, engagement rate, dan rekomendasi posting.
- **Multi-threaded & Coba Data Demo**: Proses pengambilan data berjalan di background thread sehingga GUI tetap responsif. Tersedia tombol **"✨ Coba Data Demo"** untuk pengujian langsung tanpa perlu menunggu koneksi internet.

---

## 🛠️ Cara Menjalankan Aplikasi

### Cara 1: Menggunakan File Batch (Paling Mudah)
Klik ganda pada file:
```
run.bat
```

### Cara 2: Lewat Terminal / Command Prompt
```bash
python tiktok_analytics_gui.py
```

---

## 📦 Kebutuhan Library
Library pendukung telah terpasang di sistem. Jika ingin dipasang di komputer lain:
```bash
pip install -r requirements.txt
```
*(Paket yang digunakan: `yt-dlp`, `curl_cffi`, `matplotlib`, `beautifulsoup4`)*
