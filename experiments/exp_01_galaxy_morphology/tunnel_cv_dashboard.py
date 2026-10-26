"""
tunnel_cv_dashboard.py - Persistent tunnel supervisor for Multigalaxial Life CV Dashboard (port 8505).
Includes active health monitoring and auto-restart on 502/disconnections.
"""

import subprocess
import re
import time
import os
import urllib.request
import threading

URL_FILE = r"C:\Users\HP\.gemini\antigravity\scratch\multigalaxial_life\experiments\exp_01_galaxy_morphology\LIVE_PUBLIC_URL.txt"

current_proc = None
current_url = None

def health_monitor():
    global current_proc, current_url
    fail_count = 0
    while True:
        time.sleep(20)
        if current_url and current_proc and current_proc.poll() is None:
            try:
                req = urllib.request.Request(current_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    if resp.status == 200:
                        fail_count = 0
                    else:
                        fail_count += 1
            except Exception as e:
                fail_count += 1
                print(f"[HealthCheck] Warning: {current_url} check failed ({fail_count}/2): {e}", flush=True)

            if fail_count >= 2:
                print(f"[HealthCheck] Tunnel unresponsive. Terminating process to trigger reconnect...", flush=True)
                try:
                    current_proc.terminate()
                except Exception:
                    pass
                fail_count = 0

def run_tunnel():
    global current_proc, current_url
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
    current_proc = proc
    
    url_pattern = re.compile(r"https://[a-zA-Z0-9\-_\.]+\.lhr\.life")
    
    try:
        for line in proc.stdout:
            match = url_pattern.search(line)
            if match:
                live_url = match.group(0)
                current_url = live_url
                print(f"[CV-Tunnel] ACTIVE PUBLIC URL: {live_url}", flush=True)
                with open(URL_FILE, "w") as f:
                    f.write(f"{live_url}\n")
    except Exception as e:
        print(f"[CV-Tunnel] Stream error: {e}", flush=True)
    finally:
        try:
            proc.terminate()
        except Exception:
            pass
        current_url = None
        print("[CV-Tunnel] Tunnel closed. Reconnecting...", flush=True)

def main():
    monitor_thread = threading.Thread(target=health_monitor, daemon=True)
    monitor_thread.start()
    while True:
        try:
            run_tunnel()
        except Exception as e:
            print(f"[CV-Tunnel] Exception: {e}", flush=True)
        time.sleep(3)

if __name__ == "__main__":
    main()
