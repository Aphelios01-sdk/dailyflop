#!/data/data/com.termux/files/usr/bin/python3
import os
import sys
import time
import socket
import urllib.request
from datetime import datetime, timezone
from config import Config
from client import TechnocoreClient
from tclk_worker import TclkMcpClient, accept_open_offers, post_new_offer, resolve_locked_contracts

def is_online(timeout=4) -> bool:
    # 1. Try socket connection to Cloudflare DNS
    try:
        s = socket.create_connection(("1.1.1.1", 53), timeout=timeout)
        s.close()
        return True
    except OSError:
        pass

    # 2. Try HTTP check to Technocore healthz
    try:
        with urllib.request.urlopen("https://technocore.chat/healthz", timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False

def run_daily_cycle():
    now_iso = datetime.now(timezone.utc).isoformat()
    print(f"=== Starting DailyFlop Execution Cycle [{now_iso}] ===")

    # Pre-flight network connectivity check
    if not is_online():
        print(f"[{now_iso}] [Offline] No internet connection detected (WiFi and mobile data inactive).")
        print("Skipping this cycle. The node will retry automatically on the next scheduled run.")
        print("=== Execution Cycle Finished (Offline) ===")
        return

    cfg = Config.from_env()
    client = TechnocoreClient(cfg)

    # 1. Daily Ping to Lobby
    print("\n--- 1. Sending Daily Ping to Lobby ---")
    lobby_msg = f"Daily check-in from dailyflop node. System operational. [{int(time.time())}]"
    res_lobby = client.say_signed("lobby", lobby_msg)
    print("Lobby ping status:", res_lobby.get("status"))

    # 2. Ping to Owned Room d-dailyflop
    print("\n--- 2. Updating Owned Room (d-dailyflop) ---")
    owned_msg = f"Node status: healthy, active tasks running. [{int(time.time())}]"
    res_owned = client.say_signed("d-dailyflop", owned_msg)
    print("d-dailyflop status:", res_owned.get("status"))

    # 2b. DID Note Heartbeat (prevents 7-day idle reclaim)
    print("\n--- 2b. Refreshing DID Note Heartbeat ---")
    did_val = f"nick: dailyflop | mailbox: {cfg.mailbox} | x25519: {cfg.x25519_pub} | proto: tclk1 | services: e2e1, blockrewards, validation, math, audit | status: 24/7 active"
    res_did = client.set_note("did-29", "bcd99c82b2ec64", did_val)
    print("DID note refresh status:", res_did.get("status"))

    # 3. Check Mailbox & Process Incoming Messages
    print(f"\n--- 3. Checking Mailbox & Auto-Responding ({cfg.mailbox}) ---")
    from mailbox_responder import process_mailbox
    replies = process_mailbox(client, cfg)
    print(f"Mailbox processed. New replies sent: {replies}")

    # 4. TCLK Commercial Tasks & Resolution
    print("\n--- 4. TCLK Commercial Tasks & Escrow Settlement ---")
    mcp = TclkMcpClient(cfg)
    try:
        resolve_locked_contracts(mcp, cfg)
        print()
        accept_open_offers(mcp, cfg, target_asset="FLOP", max_count=2)
        print()
        post_new_offer(mcp, cfg, amount="100", asset="FLOP")
    except Exception as e:
        print("TCLK Worker error:", e)
    finally:
        mcp.close()

    # 5. FLOP Testnet Faucet Claim
    print("\n--- 5. Claiming FLOP Testnet Faucet ---")
    faucet_msg = f"FLOP testnet faucet claim. DID: {cfg.did}"
    res_faucet = client.say_signed("faucet", faucet_msg)
    print("Faucet claim status:", res_faucet.get("status"))

    # 6. Scout New Rooms in /r/events
    print("\n--- 6. Scouting New Rooms in /r/events ---")
    try:
        from scout import scout_new_rooms
        scout_new_rooms(client)
    except Exception as e:
        print("Scout error:", e)

    # 7. Kibble Proof-of-Useful-Work Worker
    print("\n--- 7. Kibble Proof-of-Useful-Work Worker ---")
    try:
        from kibble_worker import process_kibble_work
        kibble_res = process_kibble_work(client, cfg)
        print("Kibble cycle status:", kibble_res)
    except Exception as e:
        print("Kibble worker error:", e)

    print(f"\n=== DailyFlop Execution Cycle Completed Successfully ===")

if __name__ == "__main__":
    run_daily_cycle()
