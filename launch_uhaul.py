#!/usr/bin/env python3
"""
One-command launcher for the U-Haul Space Optimizer web app.

    python launch_uhaul.py

It installs Flask if it's missing, picks a free port, opens your browser,
and prints a phone-friendly URL for anyone else on your WiFi.

Options:
    --port N        Preferred port (default 5001; auto-bumps if busy)
    --host ADDR     Bind address (default 0.0.0.0 so your phone can reach it)
    --no-browser    Don't open a browser tab automatically
"""

import argparse
import socket
import subprocess
import sys
import threading
import webbrowser


def ensure_flask() -> None:
    """Install Flask on first run so 'python launch_uhaul.py' just works."""
    try:
        import flask  # noqa: F401
        return
    except ImportError:
        pass
    print("Flask isn't installed yet — installing it now (one time only)...")
    cmd = [sys.executable, "-m", "pip", "install", "--quiet", "flask"]
    if subprocess.call(cmd) != 0 and subprocess.call(cmd + ["--user"]) != 0:
        sys.exit(
            "Couldn't install Flask automatically. Run:\n"
            f"    {sys.executable} -m pip install flask\n"
            "and then launch again."
        )


def find_free_port(preferred: int) -> int:
    """Return ``preferred`` if free, otherwise the next free port after it."""
    for port in range(preferred, preferred + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    sys.exit(f"No free port found near {preferred}.")


def lan_ip() -> str | None:
    """Best-effort LAN IP so the banner can show a phone-friendly URL."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))  # no packets sent; just picks a route
            return s.getsockname()[0]
    except OSError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch the U-Haul Space Optimizer web app.")
    parser.add_argument("--port", type=int, default=5001, help="Preferred port (default 5001).")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default 0.0.0.0).")
    parser.add_argument("--no-browser", action="store_true", help="Don't open a browser tab.")
    args = parser.parse_args()

    ensure_flask()
    from uhaul_web import app  # imported after the Flask check

    port = find_free_port(args.port)
    local_url = f"http://127.0.0.1:{port}"
    ip = lan_ip()

    print()
    print("  ┌─────────────────────────────────────────────┐")
    print("  │   🚚  U-Haul Space Optimizer is running!    │")
    print("  └─────────────────────────────────────────────┘")
    print(f"   On this computer:  {local_url}")
    if ip:
        print(f"   On your phone:     http://{ip}:{port}   (same WiFi)")
    print("   Stop with Ctrl+C")
    print()

    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(local_url)).start()

    app.run(host=args.host, port=port, debug=False)


if __name__ == "__main__":
    main()
