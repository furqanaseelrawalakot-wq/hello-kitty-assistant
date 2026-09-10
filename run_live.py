"""
run_live.py - Hello Kitty Live Public Internet Launcher.
"""

import sys
import time
import re
import threading
import subprocess
import socket
from pathlib import Path

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def drain_pipe(proc):
    try:
        for _ in iter(proc.stdout.readline, ''):
            pass
    except Exception:
        pass

def main():
    print("=" * 65, flush=True)
    print(" [HELLO KITTY] Starting Live Public Internet Service...", flush=True)
    print("=" * 65, flush=True)

    python_exe = sys.executable
    cloudflared_exe = PROJECT_ROOT / "bin" / "cloudflared.exe"

    if not cloudflared_exe.exists():
        print(f"[Error] cloudflared not found at {cloudflared_exe}", flush=True)
        sys.exit(1)

    server_proc = None
    if not is_port_in_use(5000):
        print("[1/2] Starting Hello Kitty Web Server on port 5000...", flush=True)
        server_proc = subprocess.Popen(
            [python_exe, str(PROJECT_ROOT / "web" / "app.py")],
            cwd=str(PROJECT_ROOT)
        )
        time.sleep(2)
    else:
        print("[1/2] Hello Kitty Web Server is already active on port 5000.", flush=True)

    print("[2/2] Connecting to secure Cloudflare network...", flush=True)
    cf_proc = subprocess.Popen(
        [str(cloudflared_exe), "tunnel", "--url", "http://127.0.0.1:5000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    tunnel_url = None
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    while True:
        line = cf_proc.stdout.readline()
        if not line:
            break
        match = url_pattern.search(line)
        if match:
            tunnel_url = match.group(0)
            break

    # Spawn thread to keep reading stdout so cloudflared doesn't block on full pipe buffer
    drain_thread = threading.Thread(target=drain_pipe, args=(cf_proc,), daemon=True)
    drain_thread.start()

    if tunnel_url:
        print("\n" + "=" * 65, flush=True)
        print(" *** HELLO KITTY IS NOW LIVE WORLDWIDE! ***", flush=True)
        print("=" * 65, flush=True)
        print("\n YOUR PUBLIC HTTPS URL:", flush=True)
        print(f" >>> {tunnel_url} <<<", flush=True)
        print("\n ON ANY MOBILE PHONE (iPhone & Android):", flush=True)
        print(" - Works anywhere: Mobile Data (4G/5G) or any Wi-Fi.", flush=True)
        print(" - Full microphone recording and voice replies enabled.", flush=True)
        print(" - YouTube music streaming, weather maps, and Urdu voice.", flush=True)
        print("\n Local Machine: http://127.0.0.1:5000", flush=True)
        print(" Press Ctrl+C in this terminal anytime to stop.", flush=True)
        print("=" * 65 + "\n", flush=True)
    else:
        print("[Warning] Could not parse tunnel URL automatically.", flush=True)

    try:
        while cf_proc.poll() is None:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping live service...", flush=True)
    finally:
        try:
            cf_proc.terminate()
        except Exception:
            pass
        if server_proc:
            try:
                server_proc.terminate()
            except Exception:
                pass

if __name__ == "__main__":
    main()
