#!/data/data/com.termux/files/usr/bin/python3
import os
import sys
import time
import json
import re
from config import Config
from client import TechnocoreClient

DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(DIR, "scout_state.json")
DISCOVERIES_FILE = os.path.join(DIR, "discovered_rooms.jsonl")

KEYWORDS = ["flop", "bounty", "reward", "alpha", "pool", "market", "trade", "oracle", "agent", "task"]

def load_cursor() -> int:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("last_seq", 0)
        except Exception:
            return 0
    return 0

def save_cursor(seq: int):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_seq": seq, "updated_at": int(time.time())}, f, indent=2)

def scout_new_rooms(client: TechnocoreClient) -> list:
    last_seq = load_cursor()
    print(f"Scanning /r/events for new rooms (since seq {last_seq})...")

    res = client.read_room("events", since=last_seq if last_seq > 0 else None, as_json=True)
    if res.get("status") != 200 or "data" not in res:
        print("Failed to read /r/events")
        return []

    messages = res["data"].get("messages", [])
    if not messages:
        print("No new room events.")
        return []

    max_seq = last_seq
    discoveries = []

    for m in messages:
        seq = m.get("seq", 0)
        max_seq = max(max_seq, seq)
        text = m.get("text", "")

        match = re.match(r"^created\s+([a-z0-9_-]+)", text)
        if match:
            room_name = match.group(1)
            # Check keywords
            is_relevant = any(k in room_name.lower() for k in KEYWORDS)
            
            # Fetch topic if available
            topic_res = client.get_note("topic", room_name)
            topic = topic_res.get("value", "").strip() if topic_res.get("status") == 200 else ""

            entry = {
                "seq": seq,
                "timestamp": int(time.time()),
                "room": room_name,
                "topic": topic if "404" not in topic else "",
                "is_relevant": is_relevant
            }

            if is_relevant or topic:
                print(f"  [Discovered] Room: {room_name} | Topic: {topic[:50] if topic else 'N/A'}")
                with open(DISCOVERIES_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry) + "\n")
                discoveries.append(entry)

    save_cursor(max_seq)
    print(f"Scout scan complete. Found {len(discoveries)} notable rooms.")
    return discoveries

def main():
    try:
        cfg = Config.from_env()
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)

    client = TechnocoreClient(cfg)
    scout_new_rooms(client)

if __name__ == "__main__":
    main()
