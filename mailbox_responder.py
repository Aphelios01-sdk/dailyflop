#!/data/data/com.termux/files/usr/bin/python3
import os
import sys
import time
import json
from config import Config
from client import TechnocoreClient

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mailbox_state.json")
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mailbox_log.jsonl")

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"last_seen_seq": 0}
    return {"last_seen_seq": 0}

def save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def log_interaction(entry: dict):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

def process_mailbox(client: TechnocoreClient, config: Config) -> int:
    state = load_state()
    last_seq = state.get("last_seen_seq", 0)

    res = client.read_room(config.mailbox, since=last_seq if last_seq > 0 else None, as_json=True)
    if res.get("status") != 200 or "data" not in res:
        return 0

    msgs = res["data"].get("messages", [])
    replied_count = 0
    max_seq_seen = last_seq

    for m in msgs:
        seq = m.get("seq", 0)
        if seq <= last_seq:
            continue
        max_seq_seen = max(max_seq_seen, seq)

        sender = m.get("from", "")
        text = m.get("text", "")

        # Skip messages written by our own node
        if sender == config.did:
            continue

        print(f"\n[Mailbox] New message from <{sender}>: {text}")
        
        lower_text = text.lower().strip()
        is_encrypted = False
        sender_eph_pub = None

        if text.strip().startswith("e2e1 "):
            try:
                from e2e_crypto import E2EEEngine
                e2e = E2EEEngine(config)
                decrypted, sender_eph_pub = e2e.decrypt_frame(text)
                if decrypted:
                    print(f"[Mailbox] Decrypted E2EE payload: {decrypted}")
                    text = decrypted
                    lower_text = decrypted.lower().strip()
                    is_encrypted = True
                else:
                    reply_text = "E2EE error: Unable to decrypt message with node static key."
            except Exception as e:
                reply_text = f"E2EE error: {str(e)[:80]}"

        if not is_encrypted and text.strip().startswith("e2e1 "):
            pass # reply_text already set to error above
        elif "pragma solidity" in lower_text or lower_text.startswith("audit:"):
            try:
                from audit_service import audit_solidity
                code_to_audit = text[6:].strip() if lower_text.startswith("audit:") else text
                reply_text = audit_solidity(code_to_audit)
            except Exception as e:
                reply_text = f"DailyFlop Audit Service error: {str(e)[:80]}"
        elif any(k in lower_text for k in ["gcd(", "lcm(", "sigma(", "mod ", "math:"]):
            try:
                from task_solver import solve_task
                query = text[5:].strip() if lower_text.startswith("math:") else text
                ans = solve_task(query, "p2p-query")
                reply_text = f"DailyFlop Math Solver result: {ans}"
            except Exception as e:
                reply_text = f"DailyFlop Math Solver error: {str(e)[:80]}"
        elif any(k in lower_text for k in ["ping", "status", "hello", "hi"]):
            reply_text = f"DailyFlop Node operational. DID: {config.did} | Services: E2EE ('e2e1'), Solidity audits ('audit: <code>'), Math computation ('math: <expr>'), TCLK settlements, Kibble PoUW."
        else:
            reply_text = f"Ack from dailyflop node. Received: '{text[:40]}'. Available services: send 'audit: <Solidity>' for security report, 'math: <expression>' for computation, E2EE private messages, or TCLK deals."

        # If incoming was encrypted and we have sender's ephemeral public key, encrypt the response
        if is_encrypted and sender_eph_pub:
            try:
                from e2e_crypto import E2EEEngine
                e2e = E2EEEngine(config)
                encrypted_reply = e2e.encrypt_message(sender_eph_pub, reply_text)
                if encrypted_reply:
                    reply_text = encrypted_reply
                    print("[Mailbox] Outbound reply encrypted with E2EE (AES-GCM).")
            except Exception as e:
                print(f"[Mailbox] Failed to encrypt reply: {e}")

        # Post signed reply to mailbox room
        reply_res = client.say_signed(config.mailbox, reply_text)
        print(f"Reply status: {reply_res.get('status')}")

        log_interaction({
            "timestamp": int(time.time()),
            "seq": seq,
            "from": sender,
            "incoming_text": text,
            "reply_text": reply_text,
            "status": reply_res.get("status")
        })
        replied_count += 1

    state["last_seen_seq"] = max_seq_seen
    save_state(state)
    return replied_count

def main():
    try:
        cfg = Config.from_env()
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)

    client = TechnocoreClient(cfg)
    count = process_mailbox(client, cfg)
    print(f"Processed mailbox. Replies sent: {count}")

if __name__ == "__main__":
    main()
