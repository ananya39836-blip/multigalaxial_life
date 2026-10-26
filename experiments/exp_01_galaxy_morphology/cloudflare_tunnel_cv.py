"""
cloudflare_tunnel_cv.py - Cloudflare Tunnel Daemon for Port 8505.
Provides rock-solid, ultra-fast global HTTPS access via trycloudflare.com.
"""

import subprocess
import re
import time
import os

CLOUDFLARED_BIN = r"C:\Users\HP\.gemini\antigravity\scratch\student_marks_analyzer\cloudflared.exe"
URL_FILE = r"C:\Users\HP\.gemini\antigravity\scratch\multigalaxial_life\experiments\exp_01_galaxy_morphology\CLOUDFLARE_URL.txt"

def run_tunnel():
    if not os.path.exists(CLOUDFLARED_BIN):
        print(f"[Error] cloudflared.exe not found at {CLOUDFLARED_BIN}", flush=True)
        return

    cmd = [
        CLOUDFLARED_BIN,
        "tunnel",
        "--url", "http://localhost:8505",
        "--no-autoupdate"
    ]

    print("[Cloudflare] Starting tunnel for http://localhost:8505...", flush=True)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    url_pattern = re.compile(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com")

    try:
        for line in proc.stdout:
            match = url_pattern.search(line)
            if match:
                cf_url = match.group(0)
                print(f"[Cloudflare] ACTIVE DEPLOYED URL: {cf_url}", flush=True)
                with open(URL_FILE, "w") as f:
                    f.write(f"{cf_url}\n")
    except Exception as e:
        print(f"[Cloudflare] Stream error: {e}", flush=True)
    finally:
        proc.terminate()
        print("[Cloudflare] Process terminated. Reconnecting...", flush=True)

def main():
    while True:
        try:
            run_tunnel()
        except Exception as e:
            print(f"[Cloudflare] Exception: {e}", flush=True)
        time.sleep(3)

if __name__ == "__main__":
    main()
