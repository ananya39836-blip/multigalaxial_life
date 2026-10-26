"""
pinggy_cv_dashboard.py - Persistent Pinggy tunnel supervisor for CV Dashboard (port 8505).
"""

import subprocess
import re
import time
import os

URL_FILE = r"C:\Users\HP\.gemini\antigravity\scratch\multigalaxial_life\experiments\exp_01_galaxy_morphology\LIVE_PINGGY_URL.txt"

def run_pinggy():
    cmd = [
        "ssh",
        "-p", "443",
        "-R0:localhost:8505",
        "-o", "ServerAliveInterval=15",
        "-o", "ServerAliveCountMax=3",
        "-o", "StrictHostKeyChecking=no",
        "a.pinggy.io"
    ]
    print("[Pinggy-Tunnel] Starting SSH Tunnel to pinggy.io for port 8505...", flush=True)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    url_pattern = re.compile(r"https://[a-zA-Z0-9\-_]+\.run\.pinggy-free\.link")
    try:
        for line in proc.stdout:
            match = url_pattern.search(line)
            if match:
                live_url = match.group(0)
                print(f"[Pinggy-Tunnel] ACTIVE PUBLIC URL: {live_url}", flush=True)
                with open(URL_FILE, "w") as f:
                    f.write(f"{live_url}\n")
    except Exception as e:
        print(f"[Pinggy-Tunnel] Stream error: {e}", flush=True)
    finally:
        try:
            proc.terminate()
        except Exception:
            pass
        print("[Pinggy-Tunnel] Pinggy closed. Reconnecting...", flush=True)

def main():
    while True:
        try:
            run_pinggy()
        except Exception as e:
            print(f"[Pinggy-Tunnel] Outer loop error: {e}", flush=True)
        time.sleep(5)

if __name__ == "__main__":
    main()
