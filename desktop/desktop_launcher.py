"""Desktop launcher — runs FastAPI backend + native webview window.

Used by PyInstaller to package as a standalone desktop app.
No browser needed — the app opens in its own native window.

Run: python -m app.desktop_launcher
"""
from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
import urllib.request

import uvicorn
import webview

APP_ID = "weight-health-app"


def _find_free_port() -> int:
    """Ask the OS for a free localhost port (avoids hardcoded-port collisions)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_our_server(url: str, timeout_s: float = 15.0) -> bool:
    """Poll /api/health until OUR FastAPI app answers (not just any service
    that happens to be listening on the port)."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/api/health", timeout=1.0) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                if body.get("app") == APP_ID:
                    return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


def main():
    # Ensure data directories relative to executable
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    os.makedirs(os.path.join(base, "data"), exist_ok=True)

    port = _find_free_port()

    # Start FastAPI in a daemon thread
    def run_server():
        uvicorn.run(
            "app.main:app",
            host="127.0.0.1",
            port=port,
            log_level="warning",
        )

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    url = f"http://127.0.0.1:{port}"
    if not _wait_for_our_server(url):
        # Last-resort fallback: open the window anyway so the user sees an
        # error page instead of a silent hang; the webview reload can recover.
        print(f"[launcher] warning: backend did not identify itself within timeout, opening {url} anyway", file=sys.stderr)

    # Open native window
    webview.create_window(
        title="Weight Health · 减脂记录",
        url=url,
        width=1200,
        height=800,
        min_size=(900, 600),
        text_select=True,
    )
    webview.start()


if __name__ == "__main__":
    main()
