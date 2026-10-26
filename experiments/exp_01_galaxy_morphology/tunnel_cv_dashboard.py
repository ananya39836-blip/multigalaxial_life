"""
tunnel_cv_dashboard.py - Persistent tunnel supervisor for Multigalaxial Life CV Dashboard (port 8505).
"""

import subprocess
import re
import time
import os

URL_FILE = r"C:\Users\HP\.gemini\antigravity\scratch\multigalaxial_life\experiments\exp_01_galaxy_morphology\LIVE_PUBLIC_URL.txt"

def run_tunnel():
    # Try localhost.run
    cmd = [
        "ssh",
        "-o", "ServerAliveInterval=15",
        "-o", "ServerAliveCountMax=3",
        "-o", "StrictHostKeyChecking=no",
        "-R", "80:localhost:8505",
        "nokey@localhost.run"
    ]
    
    print("[CV-Tunnel] Starting SSH Tunnel to localhost.run for port 8505...", flush=True)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    url_pattern = re.compile(r"https://[a-zA-Z0-9\-_\.]+\.lhr\.life")
    
    try:
        for line in proc.stdout:
            print(f"[Tunnel Output] {line.strip()}", flush=True)
            match = url_pattern.search(line)
            if match:
                live_url = match.group(0)
                print(f"[CV-Tunnel] ACTIVE PUBLIC URL: {live_url}", flush=True)
                with open(URL_FILE, "w") as f:
                    f.write(f"{live_url}\n")
    except Exception as e:
        print(f"[CV-Tunnel] Stream error: {e}", flush=True)
    finally:
        proc.terminate()
        print("[CV-Tunnel] Tunnel closed. Reconnecting...", flush=True)

def main():
    while True:
        try:
            run_tunnel()
        except Exception as e:
            print(f"[CV-Tunnel] Exception: {e}", flush=True)
        time.sleep(3)

if __name__ == "__main__":
    main()
