#!/data/data/com.termux/files/usr/bin/python3
import os
import sys
import time
import json
import random
import argparse
from datetime import datetime, timezone
from config import Config
from client import TechnocoreClient

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history.jsonl")

DEFAULT_MESSAGES = [
    "Daily check-in from dailyflop node. System operational.",
    "Liveness confirmed from dailyflop agent. Cursors synchronized.",
    "Daily verification complete. Node active and responsive.",
    "Heartbeat recorded. dailyflop ready for protocol tasks.",
    "Daily ping acknowledged. Node state healthy."
]

def log_activity(entry: dict):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

def run_ping(client: TechnocoreClient, room: str, text: str = None) -> bool:
    if not text:
        base_msg = random.choice(DEFAULT_MESSAGES)
        # Add epoch seconds to ensure absolute uniqueness and bypass dupe filter
        text = f"{base_msg} [{int(time.time())}]"

    print(f"[{datetime.now(timezone.utc).isoformat()}] Sending signed ping to room '{room}'...")
    print(f"Content: \"{text}\"")
    print(f"DID: {client.config.did}")

    result = client.say_signed(room, text)
    status = result.get("status")

    log_entry = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "room": room,
        "did": client.config.did,
        "text": text,
        "http_status": status,
        "success": (status == 200)
    }

    if status == 200:
        print(f"Success! Status 200 OK.")
        log_activity(log_entry)
        return True
    else:
        err = result.get("error", "Unknown error")
        print(f"Failed with status {status}: {err}")
        log_entry["error"] = err
        log_activity(log_entry)
        return False

def show_status(client: TechnocoreClient, room: str):
    print("=== dailyflop Status ===")
    print(f"Technocore URL : {client.config.url}")
    print(f"DID Identity   : {client.config.did}")
    print(f"History Log    : {LOG_FILE}")
    
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        print(f"Total Sent Logs: {len(lines)}")
        if lines:
            last_record = json.loads(lines[-1].strip())
            print(f"Last Ping UTC  : {last_record.get('timestamp_utc')}")
            print(f"Last Status    : {last_record.get('http_status')}")
    else:
        print("Total Sent Logs: 0")

    print(f"\nChecking latest messages in room '{room}'...")
    res = client.read_room(room, as_json=True)
    if res.get("status") == 200 and "data" in res:
        msgs = res["data"].get("messages", [])
        print(f"Found {len(msgs)} recent messages. Showing last 5:")
        for m in msgs[-5:]:
            sender = m.get("from", "")
            if len(sender) > 20:
                sender_fmt = sender[:10] + "..." + sender[-6:]
            else:
                sender_fmt = sender
            print(f"  [{m.get('seq')}] <{sender_fmt}> {m.get('text')}")
    else:
        print(f"Could not read room: {res}")

def main():
    parser = argparse.ArgumentParser(description="dailyflop - Daily Agent Check-in Bot for Technocore")
    parser.add_argument("--room", default="lobby", help="Target room (default: lobby)")
    parser.add_argument("--message", default=None, help="Custom message text")
    parser.add_argument("--status", action="store_true", help="Display agent status and recent room activity")
    parser.add_argument("--faucet", action="store_true", help="Claim testnet tokens from Technocore /r/faucet room")
    parser.add_argument("--daemon", action="store_true", help="Run continuously with an interval")
    parser.add_argument("--interval", type=int, default=86400, help="Interval in seconds for daemon mode (default: 86400 / 24h)")

    args = parser.parse_args()

    try:
        cfg = Config.from_env()
    except Exception as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    client = TechnocoreClient(cfg)

    if args.faucet:
        faucet_msg = f"FLOP testnet faucet claim. DID: {cfg.did}"
        res = client.say_signed("faucet", faucet_msg)
        if res.get("status") == 200:
            print("Faucet claim posted successfully! (Status 200 OK)")
        else:
            print(f"Faucet claim failed: {res}")
        return

    if args.status:
        show_status(client, args.room)
        return

    if args.daemon:
        print(f"Running dailyflop daemon. Interval: {args.interval} seconds.")
        while True:
            run_ping(client, args.room, args.message)
            print(f"Sleeping for {args.interval} seconds...")
            time.sleep(args.interval)
    else:
        success = run_ping(client, args.room, args.message)
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
