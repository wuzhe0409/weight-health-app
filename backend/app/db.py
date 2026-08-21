"""Database engine, session and initialization."""
from __future__ import annotations

import os
import sys
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import text

# PyInstaller-aware paths
if getattr(sys, "frozen", False):
    # Running as PyInstaller bundle
    BUNDLE_DIR = sys._MEIPASS
    DATA_DIR = os.path.join(os.path.expanduser("~"), ".weight-health")
    SCHEMA_PATH = os.path.join(BUNDLE_DIR, "schema.sql")
    SEED_DIR = os.path.join(BUNDLE_DIR, "seed")
else:
    # Development
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    BACKEND_DIR = os.path.dirname(APP_DIR)
    DATA_DIR = os.path.join(BACKEND_DIR, "data")
    SCHEMA_PATH = os.path.join(BACKEND_DIR, "schema.sql")
    SEED_DIR = os.path.join(BACKEND_DIR, "seed")

DB_PATH = os.path.join(DATA_DIR, "app.db")

os.makedirs(DATA_DIR, exist_ok=True)

SQLITE_URL = f"sqlite:///{DB_PATH}"
# check_same_thread=False so FastAPI threads can share the connection
engine = create_engine(SQLITE_URL, echo=False, connect_args={"check_same_thread": False})


def _migrate_v1_llm_columns(cursor) -> None:
    """v1: add LLM config columns to user_profile (schema.sql only affects new DBs)."""
    cursor.execute("PRAGMA table_info(user_profile)")
    cols = {row[1] for row in cursor.fetchall()}
    for col in ("llm_provider", "llm_base_url", "llm_api_key", "llm_model",
                "vision_api_key", "vision_base_url", "vision_model"):
        if col not in cols:
            cursor.execute(f"ALTER TABLE user_profile ADD COLUMN {col} TEXT")


def _migrate_v2_food_library(cursor) -> None:
    """v2: create food_library table (for DBs created before it existed)."""
    cursor.execute(
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
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_food_name ON food_library(name)"
    )


# Ordered migrations: (version, function). Each MUST be idempotent — DBs
# created before versioning have user_version=0 and will replay all steps.
MIGRATIONS = (
    (1, _migrate_v1_llm_columns),
    (2, _migrate_v2_food_library),
)
SCHEMA_VERSION = MIGRATIONS[-1][0]


def _run_migrations() -> None:
    """Apply pending migrations in order, tracked via PRAGMA user_version."""
    with engine.raw_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA user_version")
        current = cursor.fetchone()[0]
        for version, migrate in MIGRATIONS:
            if version > current:
                migrate(cursor)
                cursor.execute(f"PRAGMA user_version = {version}")
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
    _run_migrations()


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
