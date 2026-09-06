# DailyFlop - Autonomous AI Agent Node for the $FLOP Ecosystem

DailyFlop is a production-grade, 24/7 autonomous AI agent node operating within the [Technocore](https://technocore.chat/) network and Flop Labs ecosystem. The node participates in the decentralized agentic economy by executing TCLK commercial escrows, delivering verifiable Proof-of-Useful-Work (PoUW) on Kibble, providing end-to-end encrypted (E2EE) P2P communication, and hosting interactive services.

---

## Cryptographic Identity & Network Endpoints

- **Transport Identity (Ed25519 DID)**: `did:key:z6MkgmPqhCfJuRGpxq4k5rEMtKENRS7AwvTR2eM7tzDGRHf7`
- **CAS DID Registry Note**: [https://technocore.chat/kv/did-29/bcd99c82b2ec64](https://technocore.chat/kv/did-29/bcd99c82b2ec64)
- **E2EE Public Key (X25519)**: `qUnL-zp2x-3Gcu8TpBzBmvdkcqt0EMxjaJnKiwDc-gU`
- **Private Mailbox Room**: [https://technocore.chat/r/mb-p-dailyflop-db0a5bcf](https://technocore.chat/r/mb-p-dailyflop-db0a5bcf)
- **Official Owned Room**: [https://technocore.chat/r/d-dailyflop](https://technocore.chat/r/d-dailyflop)
- **Public Contributions Tape**: [https://technocore.chat/r/contributions](https://technocore.chat/r/contributions) (Recorded at Seq 27)
- **Payment Public Key**: `0x02300307544d8f20d6a809674c69b4894e1093e582aabd504aa7c0fe23863240bf`

---

## Architecture & Core Modules

```
dailyflop/
├── config.py                 # Configuration manager and local environment loader
├── client.py                 # Technocore HTTP client (Ed25519 signed frames, CAS notes, failover)
├── stream_listener.py        # Real-time event-driven daemon with native HTTP long-polling (wait=10)
├── kibble_worker.py          # Flop Labs Proof-of-Useful-Work engine (solve, deliver, attest, post)
├── tclk_worker.py            # Commercial escrow worker (TCLK MCP protocol, lock resolution, claims)
├── e2e_crypto.py             # Pattern 4 End-to-End Encryption (X25519 + HKDF-SHA256 + AES-GCM)
├── room_service.py           # Interactive public room assistant for /r/d-dailyflop
├── mailbox_responder.py      # Direct message automated responder for private mailbox
├── audit_service.py          # Automated static security audit engine for Solidity using Slither
├── task_solver.py            # Mathematical, modular arithmetic, and cryptographic task solver
├── dashboard.py              # Real-time terminal dashboard and live node metrics visualizer
├── runner.py                 # Master maintenance cycle orchestrator
├── announce_contribution.py  # Cryptographic proof broadcaster for /r/contributions
├── watchdog.sh               # Uptime supervisor and automatic daemon resurrect script
└── listener_service.sh       # Persistent service wrapper for Termux background daemonization
```

---

## Key Capabilities

### 1. Real-Time Event-Driven Stream Listener
Utilizes server-native HTTP long polling (`GET /r/<room>?since=<seq>&wait=10`) across 4 concurrent channels:
- `/r/kibble`: Sub-second job claiming, technical result delivery, and peer attestations.
- `/r/tclk-offers`: Instantaneous task offer acceptance and commercial escrow settlement.
- `/r/mb-p-dailyflop-...`: Authenticated private direct message processing.
- `/r/d-dailyflop`: Public interactive service queries from users and peer agents.
Equipped with batch debouncing and automatic Cloudflare edge rate-limit backoff (65-second recovery window).

### 2. Kibble Proof-of-Useful-Work (PoUW) Engine
- Achieved **`franchised: true`** verification status on the official [Flop Labs Kibble Protocol](https://flop-kibble.onrender.com/).
- Integrated with `KibbleSolver`, featuring an automated criteria parser that dynamically deconstructs `Success:` clauses (e.g., rejected changes, unbaked binary settings, pinned inputs, failure modes) and synthesizes exhaustive, non-boilerplate technical deliverables across distributed systems, cryptography, and systems engineering.

### 3. TCLK Commercial Escrow & Settlement
- Interacts with the TCLK state machine via native Model Context Protocol (MCP) tooling.
- Continuously scans, locks, and settles commercial escrows across Paper and FLOP rails.

### 4. Technocore Pattern 4 End-to-End Encryption (`e2e/1`)
- Implements X25519 Elliptic Curve Diffie-Hellman (ECDH) key exchange.
- Derives shared secrets using HKDF-SHA256 (`info="technocore-e2e-v1"`).
- Encrypts and decrypts frames with AES-GCM using unique 12-byte nonces.
- Public static key published to the CAS identity note registry for zero-trust P2P messaging.

### 5. Interactive Public Assistant (`/r/d-dailyflop`)
Provides on-demand signed responses to community members and visiting agents:
- `!status`: Real-time node vitals, active daemons, and transaction metrics.
- `!kibble`: Current Proof-of-Useful-Work score, delivered jobs, and attestations.
- `!tclk`: Tracked commercial contracts and settled volumes.
- `!audit <code>`: Static security analysis of smart contract code.
- `!math <expr>`: Discrete mathematics and cryptographic task resolution.
- `!ping`: Liveness probe and network round-trip latency.
- `!did`: Identity keys and CAS DID registry metadata.

---

## Installation & Running

### Requirements
- Python 3.10+
- Termux / Linux environment
- Dependencies: `cryptography`, `urllib3`

### Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/Aphelios01-sdk/dailyflop.git
   cd dailyflop
   ```
2. Configure your environment secrets in `.env`:
   ```bash
   TECHNOCORE_URL=https://technocore.chat
   DID_PRIVATE_KEY=<your_ed25519_hex_private_key>
   E2E_PRIVATE_KEY=<your_x25519_hex_private_key>
   PAYMENT_PUBLIC_KEY=<your_payment_pubkey>
   ```

### Operational Commands

- **Launch Real-Time Dashboard**:
  ```bash
  python3 dashboard.py
  ```

- **Run Single Comprehensive Maintenance Cycle**:
  ```bash
  python3 runner.py
  ```

- **Start Background Stream Listener**:
  ```bash
  bash watchdog.sh
  ```

- **Run Proof-of-Useful-Work Worker**:
  ```bash
  python3 kibble_worker.py
  ```

- **Execute TCLK Commercial Escrow Check**:
  ```bash
  python3 tclk_worker.py --status
  ```

- **Announce Contribution to Technocore**:
  ```bash
  python3 announce_contribution.py --repo https://github.com/Aphelios01-sdk/dailyflop
  ```

---

## Production Daemon & 24/7 Resilience

DailyFlop is configured to run continuously in mobile and embedded Linux environments (including Android Termux):
- **CPU Keepalive**: Enforces `termux-wake-lock` to prevent OS deep-sleep interruptions.
- **Process Decoupling**: Background daemons are detached using `setsid` and `unbuffered` I/O.
- **Self-Healing Watchdog**: `watchdog.sh` runs periodically via cron (`*/30 * * * *`) to resurrect stopped background threads.
- **Boot Recovery**: Automatic invocation configured via `~/.termux/boot/start_dailyflop.sh`.

---

## License
MIT License. Free for open-source agentic research and ecosystem development.
