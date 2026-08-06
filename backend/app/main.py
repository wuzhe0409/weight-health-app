"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from app.db import engine, init_db, ensure_user_profile
from app.routers import records, stats, import_export, profile, ai


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with Session(engine) as s:
        ensure_user_profile(s)
    yield


app = FastAPI(title="Weight Health App", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(records.router)
app.include_router(stats.router)
app.include_router(import_export.router)
app.include_router(profile.router)
app.include_router(ai.router)


@app.get("/")
def root():
    return {"status": "ok", "app": "weight-health-app"}
