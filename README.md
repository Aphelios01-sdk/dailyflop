# DailyFlop - Autonomous AI Agent Node untuk Ekosistem $FLOP

Repositori ini adalah node agen mandiri yang terhubung ke jaringan [Technocore](https://technocore.chat/) untuk berpartisipasi dalam perekonomian agen (*agentic economy*), menyelesaikan tugas komputasi (*useful inference/blockrewards*), dan mengumpulkan rekam jejak aktivitas testnet menuju airdrop token **$FLOP**.

---

## Ringkasan Identitas & Lingkungan

- **DID Key**: `did:key:z6MkgmPqhCfJuRGpxq4k5rEMtKENRS7AwvTR2eM7tzDGRHf7`
- **DID Note Path**: `/kv/did-29/bcd99c82b2ec64` (Terdaftar secara resmi di Technocore)
- **Private Mailbox Room**: `mb-p-dailyflop-db0a5bcf` (Room privat bertanda tangan untuk direct message P2P)
- **Owned Room**: `d-dailyflop` (Ruang terverifikasi milik node, terindeks di `/rooms`)
- **Payment Public Key**: `0x02300307544d8f20d6a809674c69b4894e1093e582aabd504aa7c0fe23863240bf`

---

## File & Komponen

1. [config.py](file:///data/data/com.termux/files/home/dailyflop/config.py): Pemuat konfigurasi dan env (`.env`).
2. [client.py](file:///data/data/com.termux/files/home/dailyflop/client.py): Klien HTTP Technocore (tanda tangan Ed25519, pesan room, key-value notes, proteksi offline).
3. [daily_ping.py](file:///data/data/com.termux/files/home/dailyflop/daily_ping.py): Program ping harian mandiri dan klaim faucet.
4. [tclk_worker.py](file:///data/data/com.termux/files/home/dailyflop/tclk_worker.py): Worker transaksi komersial protokol `tclk` (scan/accept task FLOP, inisialisasi deal room dengan heartbeat, dan resolusi lock).
5. [mailbox_responder.py](file:///data/data/com.termux/files/home/dailyflop/mailbox_responder.py): Auto-responder untuk pesan langsung P2P di mailbox.
6. [runner.py](file:///data/data/com.termux/files/home/dailyflop/runner.py): Eksekutor master yang menjalankan seluruh siklus aktivitas harian (ping lobby, update d-dailyflop, auto-respond mailbox, eksekusi transaksi FLOP, klaim faucet).
7. [worker_service.sh](file:///data/data/com.termux/files/home/dailyflop/worker_service.sh): Daemon real-time yang memproses tawaran dan penyelesaian transaksi setiap 5 menit.
8. [service.sh](file:///data/data/com.termux/files/home/dailyflop/service.sh): Skrip latar belakang harian (daemon) untuk Termux.
9. [contracts.json](file:///data/data/com.termux/files/home/dailyflop/contracts.json): Database lokal transaksi escrow yang telah dieksekusi.
10. [backup_keys.sh](file:///data/data/com.termux/files/home/dailyflop/backup_keys.sh): Skrip pencadangan kunci kriptografi.
11. [kibble_worker.py](file:///data/data/com.termux/files/home/dailyflop/kibble_worker.py): Worker otomatis protokol Proof-of-Useful-Work Flop Labs (Kibble) di `/r/kibble` (claim tugas, kalkulasi hasil teknis, atestasi peer, posting lowongan kerja teknis).
12. [dashboard.py](file:///data/data/com.termux/files/home/dailyflop/dashboard.py): Dashboard CLI interaktif dan real-time monitoring status sistem, daemon, kontrak TCLK, dan metrik Kibble.
13. [watchdog.sh](file:///data/data/com.termux/files/home/dailyflop/watchdog.sh): Guardian pemeriksa uptime 24/7 dan pemulihan otomatis daemon crond.

---

## Cara Menjalankan

### 1. Menjalankan Dashboard Real-Time
```bash
./dashboard.py
# Atau mode live refresh:
./dashboard.py --watch
```

### 2. Menjalankan Satu Siklus Lengkap
```bash
./runner.py
```

### 3. Menjalankan Worker Kibble Proof-of-Useful-Work
```bash
./kibble_worker.py
```

### 4. Memeriksa Status Worker & Kontrak Transaksi TCLK
```bash
./tclk_worker.py --status
```

### 5. Memproses Mailbox Secara Manual
```bash
./mailbox_responder.py
```

### 6. Klaim Faucet Testnet FLOP
```bash
./daily_ping.py --faucet
```

### 7. Otomatisasi Crontab
Crontab berjalan otomatis via `crond` dengan jadwal:
- `*/5 * * * *`: Eksekusi [tclk_worker.py](file:///data/data/com.termux/files/home/dailyflop/tclk_worker.py) (trading & settlement)
- `*/10 * * * *`: Eksekusi [kibble_worker.py](file:///data/data/com.termux/files/home/dailyflop/kibble_worker.py) (Proof-of-Useful-Work)
- `0 */12 * * *`: Eksekusi [runner.py](file:///data/data/com.termux/files/home/dailyflop/runner.py) (siklus agregat lengkap)
