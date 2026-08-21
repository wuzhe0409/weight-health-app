"""FastAPI application entrypoint."""
from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from app.db import engine, init_db, ensure_user_profile
from app.routers import records, stats, import_export, profile, ai, foods


# Resolve static files path (works for both dev and PyInstaller)
def _get_static_dir() -> str:
    # PyInstaller bundles data in sys._MEIPASS
    base = getattr(sys, "_MEIPASS", None)
    if base:
        path = os.path.join(base, "static")
    else:
        # Dev: frontend built output relative to backend/
        path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
    path = os.path.abspath(path)
    if os.path.isdir(path):
        return path
    return ""


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with Session(engine) as s:
        ensure_user_profile(s)
    yield


app = FastAPI(title="Weight Health App", lifespan=lifespan)

# Whitelist local dev frontend + desktop shell only. This app stores private
# health data on localhost — never allow arbitrary origins to read it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8011",
        "http://127.0.0.1:8011",
        "tauri://localhost",  # desktop wrapper
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(records.router)
app.include_router(stats.router)
app.include_router(import_export.router)
app.include_router(profile.router)
app.include_router(ai.router)
app.include_router(foods.router)


@app.get("/api/health")
def health():
    """Identity endpoint for the desktop launcher's readiness probe.

    The launcher must verify it reached OUR FastAPI app (not some other
    service squatting on a port) before opening the window.
    """
    return {"status": "ok", "app": "weight-health-app"}

# Mount static frontend (desktop/distribution mode)
static_dir = _get_static_dir()
if static_dir:
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve SPA: return index.html for all non-API paths."""
        path = os.path.join(static_dir, full_path)
        if full_path and os.path.isfile(path):
            return FileResponse(path)
        return FileResponse(os.path.join(static_dir, "index.html"))

    # Also mount assets directly for correct MIME types
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
else:
    @app.get("/")
    def root():
        return {"status": "ok", "app": "weight-health-app", "tip": "run frontend dev server at localhost:5173"}
