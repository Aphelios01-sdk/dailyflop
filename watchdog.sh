#!/data/data/com.termux/files/usr/bin/bash
# Watchdog & Uptime Guardian for DailyFlop Node

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$DIR/uptime.log"
DATE="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

# 1. Ensure Wake Lock is held
termux-wake-lock 2>/dev/null

# 2. Check and resurrect crond if dead
if ! pgrep -f crond > /dev/null; then
    echo "[$DATE] [ALERT] crond not found! Resurrecting daemon..." >> "$LOG"
    crond -p -s -m off
    echo "[$DATE] [ALERT] crond restarted with PID $(pgrep -f crond)." >> "$LOG"
else
    CRON_PID="$(pgrep -f crond | head -n 1)"
    echo "[$DATE] [OK] crond PID: $CRON_PID | WakeLock: Active" >> "$LOG"
fi

# 3. Check and resurrect stream_listener if dead
if ! pgrep -f "stream_listener.py" > /dev/null; then
    echo "[$DATE] [ALERT] stream_listener not found! Resurrecting service..." >> "$LOG"
    setsid python3 -u "$DIR/stream_listener.py" >> "$DIR/stream_service.log" 2>&1 < /dev/null &
    sleep 2
    echo "[$DATE] [ALERT] stream_listener restarted with PID $(pgrep -f "stream_listener.py" | head -n 1)." >> "$LOG"
else
    LISTENER_PID="$(pgrep -f "stream_listener.py" | head -n 1)"
    echo "[$DATE] [OK] stream_listener PID: $LISTENER_PID | Status: Active" >> "$LOG"
fi

# Keep log size bounded to last 1000 lines
tail -n 1000 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
