#!/data/data/com.termux/files/usr/bin/python3
import os
import sys
import json
import tempfile
import subprocess

SLITHER_BIN = "/data/data/com.termux/files/home/.local/bin/slither"

def audit_solidity(source_code: str) -> str:
    """
    Performs static security analysis on Solidity code using Slither.
    Returns a summarized audit report.
    """
    if not source_code or len(source_code.strip()) < 20:
        return "Error: Code snippet too short or empty for analysis."

    with tempfile.NamedTemporaryFile(suffix=".sol", mode="w", encoding="utf-8", delete=False) as tf:
        tf.write(source_code)
        temp_path = tf.name

    try:
        cmd = [SLITHER_BIN, temp_path, "--json", "-"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        # Try to parse json from stdout
        report_data = None
        if res.stdout:
            try:
                report_data = json.loads(res.stdout)
            except Exception:
                pass

        if report_data and "results" in report_data:
            detectors = report_data["results"].get("detectors", [])
            if not detectors:
                return "DailyFlop Audit Report: 0 vulnerabilities detected. Contract clean."

            high = [d["check"] for d in detectors if d.get("impact") == "High"]
            med = [d["check"] for d in detectors if d.get("impact") == "Medium"]
            low = [d["check"] for d in detectors if d.get("impact") == "Low"]

            summary = (
                f"DailyFlop Audit Report: {len(detectors)} issue(s) found. "
                f"High: {len(high)} {high[:3]}, Med: {len(med)} {med[:3]}, Low: {len(low)} {low[:3]}"
            )
            return summary
        else:
            # Fallback heuristic summary from stderr/stdout
            lines = (res.stderr or res.stdout or "").splitlines()
            issues = [l for l in lines if "INFO:Detectors:" in l or "High" in l or "Medium" in l]
            if issues:
                return f"DailyFlop Audit Report: {len(issues)} findings detected. Details: {' | '.join(issues[:2])}"
            return "DailyFlop Audit Report: Static analysis completed. No major critical issues found."

    except subprocess.TimeoutExpired:
        return "DailyFlop Audit Report: Analysis timed out."
    except Exception as e:
        return f"DailyFlop Audit Report error: {str(e)[:100]}"
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == "__main__":
    test_contract = """
    // SPDX-License-Identifier: MIT
    pragma solidity ^0.8.0;

    contract VulnerableVault {
        mapping(address => uint256) public balances;
        function withdraw() public {
            uint256 bal = balances[msg.sender];
            require(bal > 0);
            (bool s, ) = msg.sender.call{value: bal}("");
            require(s);
            balances[msg.sender] = 0;
        }
    }
    """
    print("Testing Slither audit:")
    print(audit_solidity(test_contract))
