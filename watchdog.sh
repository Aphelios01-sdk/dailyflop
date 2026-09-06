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
    echo "[$DATE] [OK] Node healthy. crond PID: $CRON_PID | WakeLock: Active" >> "$LOG"
fi

# Keep log size bounded to last 1000 lines
tail -n 1000 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
