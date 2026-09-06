#!/data/data/com.termux/files/usr/bin/python3
import os
import sys
import time
import json
import argparse
import subprocess
from config import Config

CONTRACTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contracts.json")

class TclkMcpClient:
    def __init__(self, config: Config):
        env = os.environ.copy()
        env["TECHNOCORE_URL"] = config.url
        env["TECHNOCORE_SIGNING_KEY"] = config.signing_key
        if config.payment_key:
            env["TCLK_PAYMENT_KEY"] = config.payment_key

        self.proc = subprocess.Popen(
            ["tclk-mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        self._req_id = 0
        self._call("initialize", {
            "capabilities": {},
            "clientInfo": {"name": "dailyflop-worker", "version": "1.0"},
            "protocolVersion": "2024-11-05"
        })

    def _call(self, method, params):
        self._req_id += 1
        payload = {"jsonrpc": "2.0", "id": self._req_id, "method": method, "params": params}
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            return None
        res = json.loads(line)
        return res.get("result")

    def call_tool(self, tool_name, arguments):
        res = self._call("tools/call", {"name": tool_name, "arguments": arguments})
        if res and "content" in res and len(res["content"]) > 0:
            try:
                return json.loads(res["content"][0]["text"])
            except Exception:
                return res["content"][0]["text"]
        return res

    def close(self):
        try:
            self.proc.terminate()
        except Exception:
            pass

def load_contracts() -> list:
    if os.path.exists(CONTRACTS_FILE):
        try:
            with open(CONTRACTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_contracts(contracts: list):
    with open(CONTRACTS_FILE, "w", encoding="utf-8") as f:
        json.dump(contracts, f, indent=2)

def accept_open_offers(mcp: TclkMcpClient, config: Config, target_asset: str = "FLOP", max_count: int = 2):
    print(f"Scanning 'tclk-offers' for open {target_asset} offers...")
    room_data = mcp.call_tool("tclk_read_room", {"room": "tclk-offers"})
    if not isinstance(room_data, dict) or "records" not in room_data:
        print("Failed to read tclk-offers room.")
        return

    records = room_data.get("records", [])
    offers = []
    accepted_refs = set()

    for r in records:
        line = r.get("line", "")
        if not line.startswith("tclk1 "):
            continue
        try:
            frame_raw = line[6:].strip()
            data = json.loads(frame_raw)
            ftype = data.get("type")
            if ftype == "offer":
                offers.append((line, data))
            elif ftype == "accept":
                accepted_refs.add(data.get("ref"))
        except Exception:
            continue

    contracts = load_contracts()
    known_contract_refs = {c.get("ref") for c in contracts if "ref" in c}

    count = 0
    for line, offer in reversed(offers):
        if count >= max_count:
            break

        oid = offer.get("id")
        from_did = offer.get("from")
        asset = offer.get("asset")

        if from_did == config.did:
            continue  # do not accept own offer
        if asset != target_asset and target_asset != "ANY":
            continue
        if oid in accepted_refs or oid in known_contract_refs:
            continue

        print(f"\nFound eligible offer: {oid} | Asset: {asset} | Amount: {offer.get('amount')}")
        accept_res = mcp.call_tool("tclk_accept_offer", {
            "offer": line,
            "from": config.did
        })

        if isinstance(accept_res, dict) and "line" in accept_res:
            accept_line = accept_res["line"]
            print(f"Posting accept frame for contract: {accept_res.get('contract')}")
            post_res = mcp.call_tool("tclk_post_frame", {
                "room": "tclk-offers",
                "line": accept_line
            })

            record = {
                "timestamp": int(time.time()),
                "type": "accepted",
                "status": "accepted",
                "offer_id": oid,
                "contract": accept_res.get("contract"),
                "statement": accept_res.get("statement"),
                "secret": accept_res.get("secret"),
                "dealRoom": accept_res.get("dealRoom"),
                "posted": post_res.get("posted", False) if isinstance(post_res, dict) else False
            }
            contracts.append(record)
            known_contract_refs.add(oid)
            count += 1
            print(f"Accepted successfully! Contract: {accept_res.get('contract')}")

            # Initialize deal room with heartbeat and attestation line
            droom = accept_res.get("dealRoom")
            cid = accept_res.get("contract")
            if droom and cid:
                hb = mcp.call_tool("tclk_make_heartbeat", {
                    "contract": cid,
                    "from": config.did,
                    "note": "dailyflop node operational"
                })
                if isinstance(hb, dict) and "line" in hb:
                    mcp.call_tool("tclk_post_frame", {"room": droom, "line": hb["line"]})
                    print(f"Heartbeat sent to deal room: {droom}")
                try:
                    from client import TechnocoreClient
                    from task_solver import deliver_solution
                    tc_client = TechnocoreClient(config)

                    # Extract job context
                    job_info = offer.get("job", {})
                    context_raw = job_info.get("context", "")
                    if context_raw.startswith("/kv/"):
                        parts = context_raw[4:].split("/", 1)
                        if len(parts) == 2:
                            note_res = tc_client.get_note(parts[0], parts[1])
                            if note_res.get("status") == 200:
                                context_raw = note_res.get("value", context_raw)

                    deliver_solution(tc_client, droom, cid, context_raw)
                except Exception as e:
                    print(f"Task solver error: {e}")
        else:
            print(f"Failed to accept offer: {accept_res}")

    save_contracts(contracts)
    print(f"\nAccepted {count} offers.")

def resolve_locked_contracts(mcp: TclkMcpClient, config: Config):
    contracts = load_contracts()
    updated = False

    pending = [c for c in contracts if c.get("type") == "accepted" and c.get("status") != "claimed" and "contract" in c]
    if not pending:
        print("No pending contracts requiring resolution.")
        return

    print(f"\nChecking {len(pending)} pending contracts for lock frames...")

    for c in pending:
        cid = c["contract"]
        secret = c.get("secret")
        droom = c.get("dealRoom")
        if not secret or not droom:
            continue

        lock_ref = None
        lock_rail = "paper"

        # Check dealRoom first
        room_data = mcp.call_tool("tclk_read_room", {"room": droom})
        if isinstance(room_data, dict) and "records" in room_data:
            for r in room_data["records"]:
                line = r.get("line", "")
                if line.startswith("tclk1 "):
                    try:
                        f = json.loads(line[6:].strip())
                        if f.get("type") == "lock" and f.get("contract") == cid:
                            lock_ref = f.get("ref", cid)
                            lock_rail = f.get("rail", "paper")
                            break
                    except Exception:
                        pass

        # Check tclk-offers if not found in dealRoom
        if not lock_ref:
            offers_data = mcp.call_tool("tclk_read_room", {"room": "tclk-offers"})
            if isinstance(offers_data, dict) and "records" in offers_data:
                for r in offers_data["records"]:
                    line = r.get("line", "")
                    if line.startswith("tclk1 ") and cid in line:
                        try:
                            f = json.loads(line[6:].strip())
                            if f.get("type") == "lock" and f.get("contract") == cid:
                                lock_ref = f.get("ref", cid)
                                lock_rail = f.get("rail", "paper")
                                break
                        except Exception:
                            pass

        if lock_ref:
            print(f"\nLock detected for contract {cid} on rail '{lock_rail}'!")

            # 1. Reveal
            rev = mcp.call_tool("tclk_make_reveal", {
                "contract": cid,
                "from": config.did,
                "ref": lock_ref,
                "secret": secret
            })
            if isinstance(rev, dict) and "line" in rev:
                rev_line = rev["line"]
                mcp.call_tool("tclk_post_frame", {"room": droom, "line": rev_line})
                mcp.call_tool("tclk_post_frame", {"room": "tclk-offers", "line": rev_line})
                print(f"Posted reveal frame for {cid}.")

            # 2. Receipt (claimed)
            rcpt = mcp.call_tool("tclk_make_receipt", {
                "contract": cid,
                "from": config.did,
                "outcome": "claimed",
                "rail": lock_rail,
                "ref": lock_ref
            })
            if isinstance(rcpt, dict) and "line" in rcpt:
                rcpt_line = rcpt["line"]
                mcp.call_tool("tclk_post_frame", {"room": droom, "line": rcpt_line})
                mcp.call_tool("tclk_post_frame", {"room": "tclk-offers", "line": rcpt_line})
                print(f"Posted receipt frame (claimed) for {cid}.")

            c["status"] = "claimed"
            c["settled_at"] = int(time.time())
            updated = True
            print(f"Successfully settled contract {cid} to CLAIMED status!")

    if updated:
        save_contracts(contracts)

def post_new_offer(mcp: TclkMcpClient, config: Config, amount: str = "100", asset: str = "FLOP"):
    now_ms = int(time.time() * 1000)
    expires_ms = now_ms + (20 * 60 * 1000)      # 20 min
    claim_by_ms = now_ms + (40 * 60 * 1000)     # 40 min
    refund_after_ms = now_ms + (60 * 60 * 1000) # 60 min

    task_id = f"task-dailyflop-{int(time.time())}"
    print(f"Creating new {asset} offer of {amount} minimal units...")
    offer_args = {
        "from": config.did,
        "role": "payer",
        "amount": amount,
        "asset": asset,
        "lock": "hash",
        "rails": ["paper"],
        "claimByMs": claim_by_ms,
        "refundAfterMs": refund_after_ms,
        "expiresMs": expires_ms,
        "job": {
            "proto": "blockrewards",
            "id": task_id,
            "context": f"/kv/did-29/bcd99c82b2ec64"
        }
    }

    res = mcp.call_tool("tclk_make_offer", offer_args)
    if isinstance(res, dict) and "line" in res:
        offer_line = res["line"]
        print("Posting offer frame to 'tclk-offers'...")
        post_res = mcp.call_tool("tclk_post_frame", {
            "room": "tclk-offers",
            "line": offer_line
        })
        contracts = load_contracts()
        contracts.append({
            "timestamp": int(time.time()),
            "type": "created_offer",
            "offer_id": res.get("frame", {}).get("id"),
            "task_id": task_id,
            "amount": amount,
            "asset": asset,
            "posted": post_res.get("posted", False) if isinstance(post_res, dict) else False
        })
        save_contracts(contracts)
        print(f"Offer created and posted! ID: {res.get('frame', {}).get('id')}")
    else:
        print(f"Failed to create offer: {res}")

def check_and_lock_accepted_offers(mcp: TclkMcpClient, config: Config):
    """
    Checks if any offers created by our node have been accepted by workers.
    If an accepted offer is found and not yet locked, generate and post the lock frame.
    """
    contracts = load_contracts()
    created_offers = {c.get("offer_id"): c for c in contracts if c.get("type") == "created_offer" and c.get("status") != "locked"}
    if not created_offers:
        return

    room_data = mcp.call_tool("tclk_read_room", {"room": "tclk-offers"})
    records = room_data.get("records", []) if isinstance(room_data, dict) else []

    updated = False
    for r in records:
        line = r.get("line", "")
        if line.startswith("tclk1 "):
            try:
                f = json.loads(line[6:].strip())
                if f.get("type") == "accept":
                    oid = f.get("offer")
                    if oid in created_offers:
                        entry = created_offers[oid]
                        cid = f.get("contract")
                        droom = f.get("dealRoom")
                        print(f"[Payer] Worker {f.get('from')[-8:]} accepted our offer {oid[:16]}. Locking funds for contract {cid[:16]}...")
                        lock_res = mcp.call_tool("tclk_make_lock", {
                            "contract": cid,
                            "from": config.did,
                            "rail": "paper",
                            "ref": cid
                        })
                        if isinstance(lock_res, dict) and "line" in lock_res:
                            lock_line = lock_res["line"]
                            if droom:
                                mcp.call_tool("tclk_post_frame", {"room": droom, "line": lock_line})
                            mcp.call_tool("tclk_post_frame", {"room": "tclk-offers", "line": lock_line})
                            entry["status"] = "locked"
                            entry["contract"] = cid
                            entry["dealRoom"] = droom
                            entry["locked_at"] = int(time.time())
                            updated = True
                            print(f"[Payer] Lock frame posted successfully for contract {cid[:16]}!")
            except Exception as e:
                print(f"[Payer] Error locking contract: {e}")

    if updated:
        save_contracts(contracts)

def check_and_settle_payer_contracts(mcp: TclkMcpClient, config: Config):
    """
    For offers created and locked by our node as Payer:
    Checks if the worker has posted reveal or solution in the dealRoom or tclk-offers.
    If so, post receipt frame to officially settle and mark CLAIMED!
    """
    contracts = load_contracts()
    locked_payer_contracts = [c for c in contracts if c.get("type") == "created_offer" and c.get("status") == "locked" and "contract" in c]
    if not locked_payer_contracts:
        return

    updated = False
    for c in locked_payer_contracts:
        cid = c["contract"]
        droom = c.get("dealRoom")
        revealed = False
        ref = cid
        if droom:
            room_data = mcp.call_tool("tclk_read_room", {"room": droom})
            records = room_data.get("records", []) if isinstance(room_data, dict) else []
            for r in records:
                line = r.get("line", "")
                if line.startswith("tclk1 ") and cid in line:
                    try:
                        f = json.loads(line[6:].strip())
                        if f.get("type") == "reveal" and f.get("contract") == cid:
                            revealed = True
                            ref = f.get("ref", cid)
                            break
                    except Exception:
                        pass

        if revealed:
            print(f"[Payer] Worker revealed secret for contract {cid[:16]}. Settling receipt...")
            rcpt = mcp.call_tool("tclk_make_receipt", {
                "contract": cid,
                "from": config.did,
                "outcome": "claimed",
                "rail": "paper",
                "ref": ref
            })
            if isinstance(rcpt, dict) and "line" in rcpt:
                rcpt_line = rcpt["line"]
                if droom:
                    mcp.call_tool("tclk_post_frame", {"room": droom, "line": rcpt_line})
                mcp.call_tool("tclk_post_frame", {"room": "tclk-offers", "line": rcpt_line})
                c["status"] = "claimed"
                c["settled_at"] = int(time.time())
                updated = True
                print(f"[Payer] Successfully settled contract {cid[:16]} to CLAIMED status!")

    if updated:
        save_contracts(contracts)

def auto_manage_payer_cycle(mcp: TclkMcpClient, config: Config):
    """
    Automates Payer lifecycle:
    1. Check for worker accepts and post locks
    2. Check for worker reveals and post receipts (claiming)
    3. Auto-creates a new task offer if active created offers < 2 (rate-limited to every 30m)
    """
    check_and_lock_accepted_offers(mcp, config)
    check_and_settle_payer_contracts(mcp, config)

    contracts = load_contracts()
    created_offers = [c for c in contracts if c.get("type") == "created_offer"]
    open_created = [c for c in created_offers if c.get("status") in ["open", None]]
    now = int(time.time())

    last_offer_ts = max([c.get("timestamp", 0) for c in created_offers], default=0)
    if len(open_created) < 2 and (now - last_offer_ts > 1800):
        print("[Payer] Auto-creating new task offer on tclk-offers...")
        post_new_offer(mcp, config, amount="100", asset="FLOP")

def print_status(mcp: TclkMcpClient, config: Config):
    who = mcp.call_tool("tclk_whoami", {})
    print("=== TCLK MCP Status ===")
    print(f"DID Identity  : {who.get('did')}")
    print(f"Payment PubKey: {who.get('paymentPublicKey')}")
    contracts = load_contracts()
    claimed = [c for c in contracts if c.get("status") == "claimed"]
    pending = [c for c in contracts if c.get("type") == "accepted" and c.get("status") != "claimed"]
    created = [c for c in contracts if c.get("type") == "created_offer"]
    print(f"Total Contracts Tracked : {len(contracts)}")
    print(f" - Settled (Claimed)   : {len(claimed)}")
    print(f" - Pending Resolution  : {len(pending)}")
    print(f" - Created Offers      : {len(created)}")
    if contracts:
        print("\nLast 5 events:")
        for c in contracts[-5:]:
            st = c.get("status", c.get("type"))
            print(f"  [{st}] {c.get('contract') or c.get('offer_id')} | Posted: {c.get('posted')}")

def main():
    parser = argparse.ArgumentParser(description="dailyflop - TCLK Escrow and Commercial Transaction Worker")
    parser.add_argument("--accept", action="store_true", help="Scan and accept open offers in tclk-offers")
    parser.add_argument("--resolve", action="store_true", help="Resolve locked contracts (reveal and receipt)")
    parser.add_argument("--offer", action="store_true", help="Create and post a new FLOP offer")
    parser.add_argument("--status", action="store_true", help="Show worker and contract status")
    parser.add_argument("--amount", default="100", help="Amount for new offer (default: 100)")
    parser.add_argument("--asset", default="FLOP", help="Asset to trade (default: FLOP)")
    parser.add_argument("--loop", action="store_true", help="Run in a continuous worker loop")
    parser.add_argument("--interval", type=int, default=300, help="Loop interval in seconds (default: 300)")

    args = parser.parse_args()

    try:
        cfg = Config.from_env()
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)

    mcp = TclkMcpClient(cfg)

    try:
        if args.status:
            print_status(mcp, cfg)
        elif args.offer:
            post_new_offer(mcp, cfg, amount=args.amount, asset=args.asset)
        elif args.accept:
            accept_open_offers(mcp, cfg, target_asset=args.asset)
        elif args.resolve:
            resolve_locked_contracts(mcp, cfg)
            auto_manage_payer_cycle(mcp, cfg)
        elif args.loop:
            print(f"Starting continuous worker loop every {args.interval} seconds...")
            while True:
                accept_open_offers(mcp, cfg, target_asset=args.asset)
                time.sleep(5)
                resolve_locked_contracts(mcp, cfg)
                auto_manage_payer_cycle(mcp, cfg)
                time.sleep(args.interval)
        else:
            # Default: accept, resolve, manage payer lifecycle, and print status
            accept_open_offers(mcp, cfg, target_asset=args.asset)
            resolve_locked_contracts(mcp, cfg)
            auto_manage_payer_cycle(mcp, cfg)
            print()
            print_status(mcp, cfg)
    finally:
        mcp.close()

if __name__ == "__main__":
    main()
