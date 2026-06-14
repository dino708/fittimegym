# 🏋itTime Scheduler

Sistem penjadwalan gym berbasis **Algoritma Greedy** dengan database SQLite.
Dibangun menggunakan Python + Flask.

## Fitur

### Admin
- Dashboard ringkasan (member, jadwal, bentrok)
- Penjadwalan otomatis dengan **Greedy Earliest Finish Time**
- Approve / reject jadwal member
- Manajemen alat gym (tambah, nonaktifkan, hapus)
- Lihat detail profil & waktu senggang setiap member
- Statistik: alat terpopuler, jam ramai, tujuan latihan

### Member
- Register & login akun sendiri
- Isi profil lengkap (data diri, BB/TB, tujuan latihan) → BMI otomatis
- Input waktu senggang per hari
- Daftar jadwal latihan (pilih alat, tanggal, jam)
- Lihat status jadwal (menunggu / disetujui / ditolak)

---

## Cara Menjalankan

### 1. Pastikan Python terinstal
```bash
python --version   # minimal Python 3.8
```

### 2. Install dependensi
```bash
pip install flask
```

### 3. Jalankan aplikasi
```bash
python app.py
```

### 4. Buka browser
```
http://localhost:5000
```

---

## Akun Default

| Role   | Username | Password   |
|--------|----------|------------|
| Admin  | admin    | admin123   |
| Member | andi     | member123  |
| Member | budi     | member123  |
| Member | caca     | member123  |
| Member | dani     | member123  |
| Member | eva      | member123  |

---

## truktur Proyek

```
fittime/
├── app.py                  ← Aplikasi utama Flask + semua route
├── fittime.db              ← Database SQLite (dibuat otomatis)
├── requirements.txt
└── templates/
    ├── base.html                  ← Layout + navigasi sidebar
    ├── login.html
    ├── register.html
    ├── dashboard_admin.html
    ├── dashboard_member.html
    ├── profil.html
    ├── waktu_senggang.html
    ├── jadwal_member.html
    ├── admin_jadwal.html          ← Greedy algorithm view
    ├── admin_member.html
    ├── admin_member_detail.html
    ├── admin_alat.html
    └── admin_statistik.html
```

---

## Algoritma Greedy

**Metode:** Earliest Finish Time (EFT)

1. Kelompokkan jadwal per alat gym
2. Urutkan berdasarkan jam selesai tercepat
3. Pilih jadwal pertama, lalu pilih jadwal berikutnya yang jam mulainya ≥ jam selesai jadwal sebelumnya
4. Ulangi hingga semua jadwal diproses

**Tujuan:** Memaksimalkan jumlah sesi yang bisa dilayani per alat tanpa tumpang tindih waktu.

---

## Struktur Database

| Tabel            | Isi                                      |
|------------------|------------------------------------------|
| users            | Akun admin & member, data diri lengkap   |
| alat_gym         | Nama, deskripsi, kapasitas alat          |
| jadwal           | Permintaan jadwal latihan member         |
| waktu_senggang   | Ketersediaan waktu member per hari       |
