#!/data/data/com.termux/files/usr/bin/python3
"""
DailyFlop Telegram Bot Integration
Provides push notifications for settled contracts and remote control via Telegram.
Configuration (in .env):
  TELEGRAM_BOT_TOKEN=<your_bot_token_from_botfather>
  TELEGRAM_CHAT_ID=<your_telegram_chat_id>
"""

import os
import sys
import time
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from config import Config

DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(DIR, "telegram_bot.log")

def log(msg: str):
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    line = f"[{ts}] [Telegram] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def get_telegram_creds():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token:
        # Check .env file directly if not exported in shell
        env_file = os.path.join(DIR, ".env")
        if os.path.exists(env_file):
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("TELEGRAM_BOT_TOKEN="):
                            token = line.split("=", 1)[1].strip().strip('"').strip("'")
                        elif line.startswith("TELEGRAM_CHAT_ID="):
                            chat_id = line.split("=", 1)[1].strip().strip('"').strip("'")
            except Exception:
                pass
    return token, chat_id

def send_telegram_alert(message: str) -> bool:
    """
    Sends a push notification to the configured Telegram chat ID.
    Returns True if sent, False if credentials missing or failed.
    """
    token, chat_id = get_telegram_creds()
    if not token or not chat_id:
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        log(f"Failed to send alert: {e}")
        return False

def get_node_summary() -> str:
    contracts_file = os.path.join(DIR, "contracts.json")
    kibble_file = os.path.join(DIR, "kibble_state.json")

    total_c = 0
    claimed_c = 0
    pending_c = 0
    if os.path.exists(contracts_file):
        try:
            cdata = json.load(open(contracts_file))
            total_c = len(cdata)
            claimed_c = len([c for c in cdata if c.get("status") == "claimed"])
            pending_c = len([c for c in cdata if c.get("type") == "accepted" and c.get("status") != "claimed"])
        except Exception:
            pass

    k_del = 0
    k_att = 0
    k_post = 0
    if os.path.exists(kibble_file):
        try:
            kdata = json.load(open(kibble_file))
            k_del = len(kdata.get("delivered_jobs", {}))
            k_att = len(kdata.get("attested_jobs", {}))
            k_post = len(kdata.get("posted_jobs", {}))
        except Exception:
            pass

    return (
        f"*DailyFlop Node Status*\n"
        f"Uptime: 24/7 Active (Termux)\n"
        f"Kibble PoUW: {k_del} delivered, {k_att} attested, {k_post} posted\n"
        f"TCLK Escrow: {total_c} contracts ({claimed_c} CLAIMED, {pending_c} pending)\n"
        f"Web GUI: http://localhost:8080\n"
        f"Tape Contributions: Seq 27, 28, 29"
    )

def listen_loop():
    token, default_chat_id = get_telegram_creds()
    if not token:
        log("No TELEGRAM_BOT_TOKEN provided. Telegram bot running in standby mode.")
        print("To enable Telegram alerts and remote commands, add to .env:")
        print("  TELEGRAM_BOT_TOKEN=<token_from_BotFather>")
        print("  TELEGRAM_CHAT_ID=<your_numeric_chat_id>")
        return

    log(f"Starting Telegram Bot polling listener...")
    offset = 0

    while True:
        try:
            url = f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}&timeout=20"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    chat_id = msg.get("chat", {}).get("id")
                    text = msg.get("text", "").strip()

                    if not text:
                        continue

                    log(f"Received command: '{text}' from chat {chat_id}")

                    if text in ["/start", "/help"]:
                        reply = (
                            "*DailyFlop Node Remote Control*\n"
                            "Commands:\n"
                            "/status - Real-time node vitals\n"
                            "/kibble - Proof-of-Useful-Work stats\n"
                            "/tclk   - Escrow contracts and volume\n"
                            "/pr     - Core protocol PRs summary\n"
                            "/ping   - Liveness check"
                        )
                    elif text == "/status":
                        reply = get_node_summary()
                    elif text == "/kibble":
                        reply = f"*Kibble PoUW Engine*\nLeaderboard: https://flop-kibble.onrender.com\nStatus: franchised (Active)\nDelivered: {get_node_summary().splitlines()[2]}"
                    elif text == "/tclk":
                        reply = f"*TCLK Commercial Escrow*\nTracked: {get_node_summary().splitlines()[3]}"
                    elif text == "/pr":
                        reply = (
                            "*Core Protocol Contributions (flop-labs)*\n"
                            "1. [tclk #51](https://github.com/flop-labs/tclk/pull/51) - *MERGED by sv* (c728614)\n"
                            "2. [technocore-chat #728](https://github.com/flop-labs/technocore-chat/pull/728) - 19-digit nonce precision\n"
                            "3. [technocore-chat #703](https://github.com/flop-labs/technocore-chat/pull/703) - MCP docs pagination\n"
                            "Recorded on /r/contributions: Seq 28, 29"
                        )
                    elif text == "/ping":
                        reply = f"pong | DailyFlop Node online | System time: {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC"
                    else:
                        reply = f"Unknown command: '{text}'. Send /help to see available commands."

                    # Send reply
                    reply_url = f"https://api.telegram.org/bot{token}/sendMessage"
                    payload = json.dumps({
                        "chat_id": chat_id,
                        "text": reply,
                        "parse_mode": "Markdown",
                        "disable_web_page_preview": True
                    }).encode("utf-8")
                    req_reply = urllib.request.Request(reply_url, data=payload, headers={"Content-Type": "application/json"})
                    urllib.request.urlopen(req_reply, timeout=10)

        except Exception as e:
            log(f"Polling exception: {e}")
            time.sleep(5)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--notify":
        msg = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "DailyFlop Node ping"
        success = send_telegram_alert(msg)
        print("Alert sent:", success)
    else:
        listen_loop()
