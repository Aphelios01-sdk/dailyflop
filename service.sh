#!/data/data/com.termux/files/usr/bin/bash

# DailyFlop 24/7 Daemon Service
# Runs the full cycle every 24 hours (86400 seconds) by default

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INTERVAL="${1:-86400}"

echo "Starting DailyFlop Service daemon..."
echo "Directory: $DIR"
echo "Interval: $INTERVAL seconds"

while true; do
    echo "=========================================="
    echo "Starting execution at $(date -u)"
    python3 "$DIR/runner.py"
    echo "Completed at $(date -u)"
    echo "Sleeping for $INTERVAL seconds..."
    sleep "$INTERVAL"
done
