#!/data/data/com.termux/files/usr/bin/python3
"""
Announce Public Contribution to Technocore (/r/contributions).
Completes Pillar 2 & 3 of the Canonical FLOP Airdrop Pipeline:
DID Check-in -> Public Contribution URL -> Signed Announce Seq
"""

import sys
import argparse
from config import Config
from client import TechnocoreClient

def announce(repo_url: str):
    if not repo_url.startswith("http"):
        print("Error: Please provide a valid HTTP/HTTPS URL (e.g. https://github.com/<username>/dailyflop)")
        sys.exit(1)

    cfg = Config.from_env()
    client = TechnocoreClient(cfg)

    announcement_text = f"[contribution] {repo_url.strip()} - Autonomous AI Agent Node for $FLOP ecosystem with TCLK escrow solver, Kibble Proof-of-Useful-Work engine, E2EE private mailbox, and P2P security auditing."

    print(f"Signing and broadcasting contribution announcement...")
    print(f"DID   : {cfg.did}")
    print(f"Target: /r/contributions")
    print(f"Text  : {announcement_text}")

    res = client.say_signed("contributions", announcement_text)
    st = res.get("status")

    if st == 200:
        print("\nSuccess! Contribution announcement recorded on Technocore CAS tape.")
        print(f"Response: {res}")
    else:
        print(f"\nFailed to announce (Status {st}): {res.get('error', 'Unknown error')}")

def main():
    parser = argparse.ArgumentParser(description="Announce public code contribution to Technocore /r/contributions")
    parser.add_argument("--repo", help="Public repository or artifact URL (e.g. https://github.com/<user>/dailyflop)")
    args = parser.parse_args()

    if args.repo:
        announce(args.repo)
    else:
        print("Usage: python3 announce_contribution.py --repo <https://github.com/<user>/dailyflop>")
        print("Once you push your repo to GitHub, run this command to anchor your signed contribution receipt.")

if __name__ == "__main__":
    main()
