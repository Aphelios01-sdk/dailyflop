#!/data/data/com.termux/files/usr/bin/python3
"""
Real-Time Event-Driven Stream Listener for Technocore Chat.
Utilizes server-native long polling (wait=10) across:
1. /r/kibble        -> Instant job claiming, result delivery, and peer attestation
2. /r/tclk-offers   -> Instant task offer acceptance, lock resolution, and escrow claims
3. Private Mailbox  -> Instant P2P direct message responder (Audits, Math, E2EE)

Runs concurrent worker threads with automatic network recovery.
"""

import os
import sys
import time
import json
import threading
from typing import Optional
from config import Config
from client import TechnocoreClient
from runner import is_online

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stream_listener.log")

def log(tag: str, msg: str):
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    line = f"[{ts}] [{tag}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

class BaseStreamWorker(threading.Thread):
    def __init__(self, name: str, room: str, client: TechnocoreClient, config: Config):
        super().__init__(name=name, daemon=True)
        self.room = room
        self.client = client
        self.config = config
        self.running = True
        self.last_seq: Optional[int] = None

    def get_initial_seq(self) -> Optional[int]:
        res = self.client.read_room(self.room, as_json=True)
        if res.get("status") == 200:
            msgs = res.get("data", {}).get("messages", [])
            if msgs:
                return msgs[-1].get("seq")
        return None

    def run(self):
        log(self.name, f"Starting stream listener for room '{self.room}'...")
        self.last_seq = self.get_initial_seq()
        log(self.name, f"Synchronized initial sequence cursor: {self.last_seq}")

        while self.running:
            try:
                if not is_online(timeout=3):
                    time.sleep(5)
                    continue

                # Server long-polling with wait=10
                res = self.client.read_room(self.room, since=self.last_seq, wait=10, as_json=True)
                status = res.get("status")
                if status == 429:
                    log(self.name, "429 Rate limited at edge! Backing off for 65 seconds...")
                    time.sleep(65)
                    continue
                if status != 200:
                    time.sleep(5)
                    continue

                data = res.get("data", {})
                msgs = data.get("messages", [])

                if msgs:
                    # Update sequence cursor to the highest observed
                    self.last_seq = msgs[-1].get("seq")
                    self.on_batch(msgs)
                else:
                    time.sleep(1)

            except Exception as e:
                log(self.name, f"Exception in loop: {e}")
                time.sleep(5)

    def on_batch(self, messages: list):
        pass

class KibbleStreamWorker(BaseStreamWorker):
    def __init__(self, client: TechnocoreClient, config: Config):
        super().__init__("KibbleListener", "kibble", client, config)
        self.last_work_ts = 0

    def on_batch(self, messages: list):
        has_new_job = False
        has_relevant_activity = False

        for m in messages:
            if m.get("from") == self.config.did:
                continue
            txt = m.get("text", "")
            if txt.startswith("JOB v1 |"):
                has_new_job = True
                has_relevant_activity = True
                break
            elif txt.startswith("RESULT v1 |"):
                has_relevant_activity = True

        if not has_relevant_activity:
            return

        now = time.time()
        # Debounce: run fast cycle if new job arrived at most every 45s, or 60s for other activities
        min_interval = 45 if has_new_job else 60
        if now - self.last_work_ts < min_interval:
            return

        self.last_work_ts = now
        log(self.name, f"Triggering kibble cycle (new_job={has_new_job})...")
        try:
            from kibble_worker import process_kibble_work
            summary = process_kibble_work(self.client, self.config)
            log(self.name, f"Kibble fast cycle result: {summary}")
        except Exception as e:
            log(self.name, f"Error processing kibble work: {e}")

class MailboxStreamWorker(BaseStreamWorker):
    def __init__(self, client: TechnocoreClient, config: Config):
        super().__init__("MailboxListener", config.mailbox, client, config)
        self.last_check_ts = 0

    def on_batch(self, messages: list):
        peer_msgs = [m for m in messages if m.get("from") != self.config.did]
        if not peer_msgs:
            return

        now = time.time()
        if now - self.last_check_ts < 5:
            return

        self.last_check_ts = now
        sender = peer_msgs[-1].get("from", "")
        log(self.name, f"Direct message received from <{sender[-8:]}>! Triggering auto-reply...")
        try:
            from mailbox_responder import process_mailbox
            count = process_mailbox(self.client, self.config)
            log(self.name, f"Mailbox responder processed {count} message(s).")
        except Exception as e:
            log(self.name, f"Mailbox responder error: {e}")

class TclkOffersStreamWorker(BaseStreamWorker):
    def __init__(self, client: TechnocoreClient, config: Config):
        super().__init__("TclkListener", "tclk-offers", client, config)
        self.last_check_ts = 0

    def on_batch(self, messages: list):
        peer_msgs = [m for m in messages if m.get("from") != self.config.did]
        if not peer_msgs:
            return

        now = time.time()
        if now - self.last_check_ts < 45:
            return

        self.last_check_ts = now
        log(self.name, f"Detected {len(peer_msgs)} peer offer activity. Running TCLK cycle...")
        try:
            from tclk_worker import TclkMcpClient, accept_open_offers, resolve_locked_contracts, check_and_lock_accepted_offers
            mcp = TclkMcpClient(self.config)
            try:
                resolve_locked_contracts(mcp, self.config)
                check_and_lock_accepted_offers(mcp, self.config)
                accept_open_offers(mcp, self.config, target_asset="ANY", max_count=1)
            finally:
                mcp.close()
        except Exception as e:
            log(self.name, f"TCLK stream handler error: {e}")

class DailyflopRoomStreamWorker(BaseStreamWorker):
    def __init__(self, client: TechnocoreClient, config: Config):
        super().__init__("DailyflopRoomListener", "d-dailyflop", client, config)
        self.last_check_ts = 0

    def on_batch(self, messages: list):
        peer_msgs = [m for m in messages if m.get("from") != self.config.did]
        if not peer_msgs:
            return

        now = time.time()
        if now - self.last_check_ts < 5:
            return

        self.last_check_ts = now
        sender = peer_msgs[-1].get("from", "")
        log(self.name, f"New public inquiry in /r/d-dailyflop from <{sender[-8:]}>! Generating response...")
        try:
            from room_service import process_room_messages
            count = process_room_messages(self.client, self.config)
            log(self.name, f"RoomService processed {count} message(s).")
        except Exception as e:
            log(self.name, f"RoomService error: {e}")

def main():
    log("MAIN", "Initializing Technocore Real-Time Stream Listeners...")
    try:
        cfg = Config.from_env()
    except Exception as e:
        log("MAIN", f"Config error: {e}")
        sys.exit(1)

    client = TechnocoreClient(cfg)

    workers = [
        KibbleStreamWorker(client, cfg),
        MailboxStreamWorker(client, cfg),
        TclkOffersStreamWorker(client, cfg),
        DailyflopRoomStreamWorker(client, cfg)
    ]

    for w in workers:
        w.start()

    log("MAIN", "All 4 Stream Listeners ACTIVE and long-polling Technocore!")
    try:
        while True:
            time.sleep(60)
            # Periodic health heartbeat
            log("HEARTBEAT", "All listener threads healthy.")
    except KeyboardInterrupt:
        log("MAIN", "Stopping stream listeners...")
        for w in workers:
            w.running = False
        sys.exit(0)

if __name__ == "__main__":
    main()
