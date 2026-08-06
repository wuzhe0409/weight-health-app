"""Desktop launcher — runs uvicorn in a windowless mode.

Used by PyInstaller to package as a standalone app.
The FastAPI server serves both API and static frontend on :8011,
then auto-opens the browser.

Run: python -m app.desktop_launcher
"""
from __future__ import annotations

import os
import sys
import threading
import webbrowser
import time

import uvicorn


def _open_browser():
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:8011")


def main():
    # Ensure data directories relative to executable
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    os.makedirs(os.path.join(base, "data"), exist_ok=True)

    threading.Thread(target=_open_browser, daemon=True).start()

    # Use app.main:app with lifespan handler
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8011,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
