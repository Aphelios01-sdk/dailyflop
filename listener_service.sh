#!/data/data/com.termux/files/usr/bin/bash
# Technocore Real-Time Stream Listener Service Daemon

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

while true; do
    echo "[$(date -u)] Starting stream_listener.py..." >> "$DIR/stream_service.log"
    python3 "$DIR/stream_listener.py" >> "$DIR/stream_service.log" 2>&1
    echo "[$(date -u)] stream_listener exited. Restarting in 5s..." >> "$DIR/stream_service.log"
    sleep 5
done
