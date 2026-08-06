"""Database engine, session and initialization."""
from __future__ import annotations

import os
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import text

# Paths
APP_DIR = os.path.dirname(os.path.abspath(__file__))            # backend/app
BACKEND_DIR = os.path.dirname(APP_DIR)                           # backend
DATA_DIR = os.path.join(BACKEND_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "app.db")
SCHEMA_PATH = os.path.join(BACKEND_DIR, "schema.sql")

os.makedirs(DATA_DIR, exist_ok=True)

SQLITE_URL = f"sqlite:///{DB_PATH}"
# check_same_thread=False so FastAPI threads can share the connection
engine = create_engine(SQLITE_URL, echo=False, connect_args={"check_same_thread": False})


def _migrate_existing_db() -> None:
    """Add LLM columns to existing user_profile table (schema.sql only affects new DBs)."""
    with engine.raw_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(user_profile)")
        cols = {row[1] for row in cursor.fetchall()}
        for col in ("llm_provider", "llm_base_url", "llm_api_key", "llm_model",
                  "vision_api_key", "vision_base_url", "vision_model"):
            if col not in cols:
                cursor.execute(f"ALTER TABLE user_profile ADD COLUMN {col} TEXT")
        conn.commit()


def init_db() -> None:
    """Create tables from schema.sql (idempotent: all CREATE TABLE IF NOT EXISTS)."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    # Use the raw DBAPI connection: it exposes executescript (SQLAlchemy 2.x
    # Connection does not), so we can run PRAGMA + all CREATE TABLEs at once.
    with engine.raw_connection() as conn:
        conn.executescript(schema_sql)
        conn.commit()
    _migrate_existing_db()
    _migrate_food_library()


def _migrate_food_library() -> None:
    """Create food_library table if it doesn't exist (for existing DBs)."""
    with engine.raw_connection() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS food_library ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  name TEXT NOT NULL,"
            "  category TEXT DEFAULT 'other',"
            "  calories_per_100g REAL,"
            "  protein_per_100g REAL,"
            "  carbs_per_100g REAL,"
            "  fat_per_100g REAL,"
            "  common_portion TEXT,"
            "  common_portion_g REAL,"
            "  common_portion_kcal REAL,"
            "  is_custom INTEGER DEFAULT 0,"
            "  user_id INTEGER,"
            "  created_at TEXT"
            ")"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_food_name ON food_library(name)"
        ))
        conn.commit()


def get_session():
    """FastAPI dependency that yields a DB session."""
    with Session(engine) as session:
        yield session


def ensure_user_profile(session: Session) -> None:
    """Insert the default single-row user profile if it does not exist."""
    from app.models import UserProfile
    existing = session.get(UserProfile, 1)
    if existing is None:
        session.add(
            UserProfile(
                id=1,
                gender="female",
                age=30,
                height_cm=160.0,
                frame_size="small_medium",
                target_weight_kg=48.0,
                bmr_formula="Mifflin-St Jeor",
                llm_provider="openai",
                llm_model="gpt-4o-mini",
            )
        )
        session.commit()
