#!/data/data/com.termux/files/usr/bin/bash

# Script untuk menampilkan kunci privat dan identitas penting
# Simpan nilai-nilai ini di tempat yang aman (misal password manager terenkripsi)

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$DIR/.env" ]; then
    echo "========================================================"
    echo "        KUNCI IDENTITAS & PEMBAYARAN DAILYFLOP         "
    echo "========================================================"
    cat "$DIR/.env"
    echo "========================================================"
    echo "PERINGATAN: Jaga kerahasiaan TECHNOCORE_SIGNING_KEY dan"
    echo "TCLK_PAYMENT_KEY. Jangan bagikan kepada siapa pun."
    echo "========================================================"
else
    echo "File .env tidak ditemukan di $DIR"
fi
