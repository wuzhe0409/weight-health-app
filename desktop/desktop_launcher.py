"""Desktop launcher — runs FastAPI backend + native webview window.

Used by PyInstaller to package as a standalone desktop app.
No browser needed — the app opens in its own native window.

Run: python -m app.desktop_launcher
"""
from __future__ import annotations

import os
import sys
import threading
import time

import uvicorn
import webview


def main():
    # Ensure data directories relative to executable
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    os.makedirs(os.path.join(base, "data"), exist_ok=True)

    # Start FastAPI in a daemon thread
    def run_server():
        uvicorn.run(
            "app.main:app",
            host="127.0.0.1",
            port=8011,
            log_level="warning",
        )

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Wait for server to be ready
    url = "http://127.0.0.1:8011"
    for _ in range(30):
        try:
            import urllib.request
            urllib.request.urlopen(url, timeout=0.5)
            break
        except Exception:
            time.sleep(0.2)

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
