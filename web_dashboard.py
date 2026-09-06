#!/data/data/com.termux/files/usr/bin/python3
"""
DailyFlop Web Dashboard GUI (http://localhost:8080)
Lightweight, zero-dependency local monitoring server for Google Chrome on Android.
Provides real-time dark-mode visual interface with auto-refreshing JSON telemetry.
"""

import os
import sys
import time
import json
import subprocess
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from config import Config

DIR = os.path.dirname(os.path.abspath(__file__))
CONTRACTS_FILE = os.path.join(DIR, "contracts.json")
KIBBLE_STATE_FILE = os.path.join(DIR, "kibble_state.json")
ROOM_SERVICE_LOG = os.path.join(DIR, "room_service_log.jsonl")
STREAM_LOG = os.path.join(DIR, "stream_listener.log")
UPTIME_LOG = os.path.join(DIR, "uptime.log")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DailyFlop Node | Real-Time Control Center</title>
  <style>
    :root {
      --bg: #090d13;
      --card-bg: #111822;
      --card-border: #1e293b;
      --accent: #00f0ff;
      --accent-dim: #00a3b4;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --font-mono: 'Courier New', Courier, monospace;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      padding: 16px;
      line-height: 1.5;
    }
    .container { max-width: 1100px; margin: 0 auto; }
    header {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 16px;
      margin-bottom: 20px;
      border-bottom: 1px solid var(--card-border);
      gap: 12px;
    }
    .brand { display: flex; align-items: center; gap: 12px; }
    .brand h1 { font-size: 1.4rem; font-weight: 700; letter-spacing: 0.5px; }
    .badge {
      font-size: 0.75rem;
      padding: 3px 8px;
      border-radius: 4px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .badge-success { background: rgba(16, 185, 129, 0.2); color: var(--success); border: 1px solid var(--success); }
    .badge-accent { background: rgba(0, 240, 255, 0.15); color: var(--accent); border: 1px solid var(--accent); }
    .clock { font-family: var(--font-mono); font-size: 0.85rem; color: var(--text-muted); }
    
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 20px; }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 16px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
    .card-title { font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; margin-bottom: 8px; }
    .card-val { font-size: 1.8rem; font-weight: 700; color: var(--accent); font-family: var(--font-mono); }
    .card-sub { font-size: 0.8rem; color: var(--text-muted); margin-top: 4px; }
    
    .section-title { font-size: 1.1rem; font-weight: 700; margin: 24px 0 12px 0; display: flex; justify-content: space-between; align-items: center; }
    .table-container { overflow-x: auto; background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 8px; }
    table { width: 100%; border-collapse: collapse; text-align: left; font-size: 0.85rem; }
    th, td { padding: 12px 16px; border-bottom: 1px solid var(--card-border); }
    th { color: var(--text-muted); font-weight: 600; text-transform: uppercase; font-size: 0.75rem; }
    tr:last-child td { border-bottom: none; }
    
    .status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
    .dot-green { background: var(--success); box-shadow: 0 0 6px var(--success); }
    .dot-red { background: var(--danger); box-shadow: 0 0 6px var(--danger); }
    
    .code-box {
      background: #05080c;
      border: 1px solid #1e293b;
      padding: 12px;
      border-radius: 6px;
      font-family: var(--font-mono);
      font-size: 0.8rem;
      color: #38bdf8;
      word-break: break-all;
      margin-bottom: 12px;
    }
    .pr-badge {
      display: inline-block;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
    }
    .pr-merged { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #10b981; }
    .pr-open { background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid #3b82f6; }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }
    .log-box {
      background: #030712;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 12px;
      font-family: var(--font-mono);
      font-size: 0.75rem;
      max-height: 240px;
      overflow-y: auto;
      color: #94a3b8;
      white-space: pre-wrap;
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand">
        <h1>DAILYFLOP NODE</h1>
        <span class="badge badge-accent">Technocore Agent</span>
        <span class="badge badge-success">Franchised</span>
      </div>
      <div class="clock" id="clock">Syncing...</div>
    </header>

    <!-- Metrics Cards -->
    <div class="grid">
      <div class="card">
        <div class="card-title">Kibble PoUW Delivered</div>
        <div class="card-val" id="kibble-delivered">--</div>
        <div class="card-sub" id="kibble-sub">Attestations: -- | Posted: --</div>
      </div>
      <div class="card">
        <div class="card-title">TCLK Escrow Contracts</div>
        <div class="card-val" id="tclk-total">--</div>
        <div class="card-sub" id="tclk-sub">Settled: -- | Pending: --</div>
      </div>
      <div class="card">
        <div class="card-title">Daemon & Stream Status</div>
        <div class="card-val" id="daemon-val" style="font-size: 1.2rem; margin-top: 6px;">--</div>
        <div class="card-sub" id="daemon-sub">4 Stream Listeners Active</div>
      </div>
      <div class="card">
        <div class="card-title">Core Protocol PRs</div>
        <div class="card-val" id="pr-val">12</div>
        <div class="card-sub"><span class="pr-badge pr-merged">PR #51 MERGED by sv</span></div>
      </div>
    </div>

    <!-- Node Identity -->
    <div class="section-title">Cryptographic Identity & Network</div>
    <div class="code-box">
      <strong>Transport DID:</strong> <span id="did-str">Loading...</span><br>
      <strong>X25519 E2EE Pubkey:</strong> qUnL-zp2x-3Gcu8TpBzBmvdkcqt0EMxjaJnKiwDc-gU<br>
      <strong>Public Room:</strong> <a href="https://technocore.chat/r/d-dailyflop" target="_blank">https://technocore.chat/r/d-dailyflop</a><br>
      <strong>Contributions Tape:</strong> <a href="https://technocore.chat/r/contributions" target="_blank">/r/contributions (Seq 27, 28, 29)</a><br>
      <strong>GitHub Repository:</strong> <a href="https://github.com/Aphelios01-sdk/dailyflop" target="_blank">https://github.com/Aphelios01-sdk/dailyflop</a>
    </div>

    <!-- Core Protocol PRs Table -->
    <div class="section-title">Core Protocol Contributions (flop-labs)</div>
    <div class="table-container">
      <table>
        <thead>
          <tr>
            <th>Repository</th>
            <th>Number</th>
            <th>Status</th>
            <th>Title & Scope</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>flop-labs/tclk</td>
            <td><strong>#51</strong></td>
            <td><span class="pr-badge pr-merged">MERGED (by sv)</span></td>
            <td>fix: reject contradictory receipt rail/ref and zero adaptor witness</td>
          </tr>
          <tr>
            <td>flop-labs/technocore-chat</td>
            <td>#728</td>
            <td><span class="pr-badge pr-open">OPEN</span></td>
            <td>fix(humans): preserve 19-digit nonce precision in newest delegation resolution</td>
          </tr>
          <tr>
            <td>flop-labs/technocore-chat</td>
            <td>#703</td>
            <td><span class="pr-badge pr-open">OPEN</span></td>
            <td>fix(mcp): describe read_docs page parameter (#698)</td>
          </tr>
          <tr>
            <td>flop-labs/tclk</td>
            <td>#82</td>
            <td><span class="pr-badge pr-open">OPEN</span></td>
            <td>fix(transcript): preserve exact nonces above 2^53 in export and room parsing</td>
          </tr>
          <tr>
            <td>flop-labs/tclk</td>
            <td>#32</td>
            <td><span class="pr-badge pr-open">OPEN</span></td>
            <td>fix(machine): bind proposed-state cancel to offer id and permit receipt</td>
          </tr>
          <tr>
            <td>flop-labs/technocore-chat</td>
            <td>#240</td>
            <td><span class="pr-badge pr-open">OPEN</span></td>
            <td>fix(store): isolate concurrent note count rewrites</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Live Node Logs -->
    <div class="section-title">Live Activity Log (Recent)</div>
    <div class="log-box" id="log-box">Connecting to local node telemetry stream...</div>
  </div>

  <script>
    async function updateDashboard() {
      try {
        const res = await fetch('/api/status');
        const data = await res.json();
        
        document.getElementById('clock').innerText = data.system_time + ' (UTC)';
        document.getElementById('kibble-delivered').innerText = data.kibble_delivered;
        document.getElementById('kibble-sub').innerText = 'Attestations: ' + data.kibble_attested + ' | Jobs Posted: ' + data.kibble_posted;
        
        document.getElementById('tclk-total').innerText = data.contracts_total;
        document.getElementById('tclk-sub').innerText = 'Settled (Claimed): ' + data.contracts_claimed + ' | Pending: ' + data.contracts_pending;
        
        document.getElementById('daemon-val').innerText = data.stream_status.includes('ACTIVE') ? 'ONLINE (24/7)' : 'STOPPED';
        document.getElementById('daemon-val').style.color = data.stream_status.includes('ACTIVE') ? '#10b981' : '#ef4444';
        document.getElementById('daemon-sub').innerText = 'crond: ' + data.crond_status + ' | WakeLock: ' + data.wakelock;
        
        document.getElementById('did-str').innerText = data.did;
        
        if (data.recent_logs) {
          document.getElementById('log-box').innerText = data.recent_logs;
        }
      } catch (err) {
        console.error('Failed to sync telemetry:', err);
      }
    }
    setInterval(updateDashboard, 3000);
    updateDashboard();
  </script>
</body>
</html>
"""

def load_json(filepath, default=None):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default

def get_process_status(name: str):
    try:
        res = subprocess.run(["pgrep", "-fa", name], capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            lines = [l for l in res.stdout.strip().splitlines() if not "web_dashboard.py" in l]
            if lines:
                return "ACTIVE (PID: " + lines[0].split()[0] + ")"
    except Exception:
        pass
    return "STOPPED"

def get_recent_logs():
    lines = []
    if os.path.exists(STREAM_LOG):
        try:
            with open(STREAM_LOG, "r", encoding="utf-8") as f:
                lines = f.readlines()[-15:]
        except Exception:
            pass
    return "".join(lines) if lines else "No stream activity recorded yet."

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
        elif self.path == "/api/status":
            cfg = Config.from_env()
            contracts = load_json(CONTRACTS_FILE, [])
            claimed = [c for c in contracts if c.get("status") == "claimed"]
            pending = [c for c in contracts if c.get("type") == "accepted" and c.get("status") != "claimed"]
            
            kibble = load_json(KIBBLE_STATE_FILE, {})
            delivered = len(kibble.get("delivered_jobs", {}))
            attested = len(kibble.get("attested_jobs", {}))
            posted = len(kibble.get("posted_jobs", {}))

            status_payload = {
                "system_time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "did": cfg.did,
                "contracts_total": len(contracts),
                "contracts_claimed": len(claimed),
                "contracts_pending": len(pending),
                "kibble_delivered": delivered,
                "kibble_attested": attested,
                "kibble_posted": posted,
                "crond_status": get_process_status("crond"),
                "stream_status": get_process_status("stream_listener.py"),
                "wakelock": "Active",
                "recent_logs": get_recent_logs()
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(status_payload).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Silence standard HTTP access logs to keep terminal quiet
        return

def run_server(port=8080):
    server_address = ("0.0.0.0", port)
    httpd = HTTPServer(server_address, DashboardHandler)
    print(f"DailyFlop Web Dashboard running at http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down dashboard server...")
        httpd.server_close()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port)
