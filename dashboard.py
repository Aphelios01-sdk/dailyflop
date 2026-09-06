#!/data/data/com.termux/files/usr/bin/python3
import os
import sys
import time
import json
import subprocess
from datetime import datetime, timezone
from config import Config

DIR = os.path.dirname(os.path.abspath(__file__))
CONTRACTS_FILE = os.path.join(DIR, "contracts.json")
CRON_LOG = os.path.join(DIR, "cron.log")
WORKER_LOG = os.path.join(DIR, "worker_loop.log")
MAILBOX_LOG = os.path.join(DIR, "mailbox_log.jsonl")

def get_process_status(name: str):
    try:
        res = subprocess.run(["pgrep", "-fa", name], capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            # Exclude current process or grep itself
            lines = [l for l in res.stdout.strip().splitlines() if not "dashboard.py" in l]
            if lines:
                return "ACTIVE (PID: " + lines[0].split()[0] + ")"
    except Exception:
        pass
    return "STOPPED"

def get_cron_schedule():
    try:
        res = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        if res.returncode == 0:
            lines = [l for l in res.stdout.splitlines() if l.strip() and not l.startswith("#") and not "=" in l]
            return f"{len(lines)} job(s) active"
    except Exception:
        pass
    return "UNKNOWN"

def load_json(filepath: str, default=None):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def render_dashboard(cfg: Config):
    contracts = load_json(CONTRACTS_FILE, [])
    claimed = [c for c in contracts if c.get("status") == "claimed"]
    pending = [c for c in contracts if c.get("type") == "accepted" and c.get("status") != "claimed"]
    created = [c for c in contracts if c.get("type") == "created_offer"]

    # Calculate FLOP volumes
    claimed_vol = sum(int(c.get("amount", 0)) for c in claimed if "amount" in c)

    crond_status = get_process_status("crond")
    cron_sched = get_cron_schedule()

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("\033[2J\033[H", end="") # Clear terminal
    print("==========================================================================")
    print("                   DAILYFLOP NODE - REAL-TIME DASHBOARD                   ")
    print(f"                       System Time: {now_str}                       ")
    print("==========================================================================")
    print(f" DID Transport Identity : {cfg.did}")
    print(f" DID Note Registry      : https://technocore.chat/kv/did-29/bcd99c82b2ec64")
    print(f" Private Mailbox Room   : https://technocore.chat/r/{cfg.mailbox}")
    print(f" Official Owned Room    : https://technocore.chat/r/d-dailyflop")
    print(f" Payment Public Key     : {cfg.payment_key[:20]}...{cfg.payment_key[-10:] if cfg.payment_key else 'None'}")
    print(f" E2EE X25519 Public Key : {cfg.x25519_pub}")
    print("--------------------------------------------------------------------------")
    listener_status = get_process_status("stream_listener")
    print(" SYSTEM & DAEMON STATUS:")
    print(f"  * Cron Service (crond): {crond_status}")
    print(f"  * Stream Listener     : {listener_status}")
    print(f"  * Crontab Active Jobs : {cron_sched}")
    print(f"  * Wake Lock State     : ACTIVE")
    print(f"  * Termux:Boot Script  : INSTALLED (~/.termux/boot/start_dailyflop.sh)")
    print("--------------------------------------------------------------------------")
    print(" TCLK ESCROW & COMMERCIAL TRANSACTIONS:")
    print(f"  * Total Contracts Tracked : {len(contracts)}")
    print(f"  * Settled / Claimed       : {len(claimed)}")
    print(f"  * Pending Payer Lock      : {len(pending)}")
    print(f"  * Created Task Offers     : {len(created)}")
    print("--------------------------------------------------------------------------")
    print(" RECENT CONTRACT EVENTS (LAST 5):")
    if contracts:
        for c in contracts[-5:]:
            st = c.get("status", c.get("type"))
            cid = c.get("contract") or c.get("offer_id") or "N/A"
            cid_short = cid[:12] + "..." + cid[-8:] if len(cid) > 20 else cid
            amt = f" | Amount: {c.get('amount')} FLOP" if "amount" in c else ""
            print(f"  [{st.upper():<9}] ID: {cid_short}{amt}")
    else:
        print("  (No contracts tracked yet)")
    # Kibble Proof-of-Useful-Work metrics
    kibble_state = load_json(os.path.join(DIR, "kibble_state.json"), {})
    k_delivered = len(kibble_state.get("delivered_jobs", {}))
    k_attested = len(kibble_state.get("attested_jobs", {}))
    k_posted = len(kibble_state.get("posted_jobs", {}))

    print("--------------------------------------------------------------------------")
    print(" KIBBLE PROOF-OF-USEFUL-WORK (FLOP LABS PROTOCOL):")
    print(f"  * Results Delivered (Franchise Active) : {k_delivered}")
    print(f"  * Peer Attestations Given (Useful x6)  : {k_attested}")
    print(f"  * Technical Jobs Posted (Jobs x2)      : {k_posted}")
    print(f"  * Public Protocol Board                : https://technocore.chat/r/kibble")
    print("--------------------------------------------------------------------------")
    print(" LAST ACTIVITY LOGS:")
    if os.path.exists(CRON_LOG):
        with open(CRON_LOG, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        if lines:
            print(f"  Cron: {lines[-1]}")
    if os.path.exists(WORKER_LOG):
        with open(WORKER_LOG, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        if lines:
            print(f"  Worker: {lines[-1]}")
    print("==========================================================================")
    print(" Press Ctrl+C to exit dashboard view.")

def main():
    watch_mode = "--watch" in sys.argv
    try:
        cfg = Config.from_env()
    except Exception as e:
        print(f"Config error: {e}", file=sys.stderr)
        sys.exit(1)

    if watch_mode:
        try:
            while True:
                render_dashboard(cfg)
                time.sleep(3)
        except KeyboardInterrupt:
            print("\nDashboard closed.")
    else:
        render_dashboard(cfg)

if __name__ == "__main__":
    main()
