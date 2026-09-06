#!/data/data/com.termux/files/usr/bin/bash

# TCLK Real-Time Escrow & Task Worker Daemon
# Runs every 5 minutes (300 seconds) by default

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INTERVAL="${1:-300}"

echo "Starting TCLK Worker Service in background..."
echo "Directory: $DIR"
echo "Interval: $INTERVAL seconds"

while true; do
    echo "--- Cycle started: $(date -u) ---" >> "$DIR/worker_loop.log"
    python3 "$DIR/tclk_worker.py" --accept >> "$DIR/worker_loop.log" 2>&1
    python3 "$DIR/tclk_worker.py" --resolve >> "$DIR/worker_loop.log" 2>&1
    python3 "$DIR/kibble_worker.py" >> "$DIR/worker_loop.log" 2>&1
    echo "--- Cycle finished: $(date -u) ---" >> "$DIR/worker_loop.log"
    sleep "$INTERVAL"
done
