#!/data/data/com.termux/files/usr/bin/python3
"""
DailyFlop Automated Backup Manager
Creates compressed snapshots of node state, cryptographic keys, and contracts.
Stores redundant archives in:
1. /sdcard/Download/dailyflop_backup/ (Directly accessible via Android File Manager)
2. ~/dailyflop_backup/ (Internal Termux persistent storage)
Maintains rolling retention of the last 7 backups.
"""

import os
import sys
import time
import tarfile
import shutil
from datetime import datetime, timezone

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
SDCARD_DIR = "/sdcard/Download/dailyflop_backup"
INTERNAL_BACKUP_DIR = os.path.expanduser("~/dailyflop_backup")

FILES_TO_BACKUP = [
    ".env",
    "contracts.json",
    "kibble_state.json",
    "room_service_state.json",
    "mailbox_state.json"
]

def ensure_dirs():
    for d in [INTERNAL_BACKUP_DIR, SDCARD_DIR]:
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            pass

def prune_old_backups(directory: str, max_count: int = 7):
    if not os.path.exists(directory):
        return
    try:
        files = [os.path.join(directory, f) for f in os.listdir(directory) if f.startswith("dailyflop_backup_") and f.endswith(".tar.gz")]
        files.sort(key=os.path.getmtime)
        while len(files) > max_count:
            oldest = files.pop(0)
            os.remove(oldest)
            print(f"[Backup] Pruned old backup: {os.path.basename(oldest)}")
    except Exception as e:
        print(f"[Backup] Prune error in {directory}: {e}")

def create_backup() -> str:
    ensure_dirs()
    ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive_name = f"dailyflop_backup_{ts_str}.tar.gz"
    temp_tar = os.path.join(SRC_DIR, archive_name)

    print(f"[Backup] Starting backup cycle at {ts_str} UTC...")
    with tarfile.open(temp_tar, "w:gz") as tar:
        for fname in FILES_TO_BACKUP:
            fpath = os.path.join(SRC_DIR, fname)
            if os.path.exists(fpath):
                tar.add(fpath, arcname=fname)
                print(f"  + Included: {fname}")
            else:
                print(f"  - Skipped (absent): {fname}")

    # Copy to internal backup
    if os.path.exists(INTERNAL_BACKUP_DIR):
        dest_internal = os.path.join(INTERNAL_BACKUP_DIR, archive_name)
        shutil.copy2(temp_tar, dest_internal)
        print(f"[Backup] Saved to internal storage: {dest_internal}")
        prune_old_backups(INTERNAL_BACKUP_DIR, max_count=7)

    # Copy to /sdcard/Download
    if os.path.exists(SDCARD_DIR):
        dest_sdcard = os.path.join(SDCARD_DIR, archive_name)
        shutil.copy2(temp_tar, dest_sdcard)
        print(f"[Backup] Saved to Android storage: {dest_sdcard}")
        prune_old_backups(SDCARD_DIR, max_count=7)

    # Remove temporary file in project directory
    if os.path.exists(temp_tar):
        os.remove(temp_tar)

    print(f"[Backup] Backup cycle completed successfully.")
    return archive_name

if __name__ == "__main__":
    create_backup()
