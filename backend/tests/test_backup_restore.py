"""Regression tests for /api/import/backup (JSON backup restore).

Guards three data-integrity bugs fixed 2026-08-21:
  1. food_entries must be restored WITH kcal/kcal_min/kcal_max/quantity_g
     (previously silently dropped — violated the min/max preservation rule).
  2. weight_measurements with missing/zero weight_kg must be SKIPPED
     (previously fabricated a 0kg measurement that poisoned trend stats).
  3. A record that fails mid-restore must be rolled back entirely
     (previously a half-written record — no food entries — got committed).

Runs against a throwaway SQLite DB via dependency override; never touches
the real app.db.
"""
import io
import json
import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine, select

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import get_session
from app.main import app
from app.models import DailyRecord, FoodEntry, WeightMeasurement


@pytest.fixture()
def client(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path}/test.db",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    yield TestClient(app), engine
    app.dependency_overrides.clear()


def _post_backup(client, records: list, dry_run: bool = False):
    payload = json.dumps(records).encode("utf-8")
    return client.post(
        f"/api/import/backup?dry_run={'true' if dry_run else 'false'}",
        files={"file": ("backup.json", io.BytesIO(payload), "application/json")},
    )


def _sample_record(date="2026-08-01"):
    return {
        "record_date": date,
        "weight_kg": 49.5,
        "bowel_movement": "yes",
        "total_kcal_min": 1000,
        "total_kcal_max": 1300,
        "data_status": "estimated",
        "food_entries": [
            {
                "meal_type": "breakfast",
                "food_name": "包子",
                "quantity_text": "1个",
                "quantity_g": 120.0,
                "kcal": 220.0,
                "kcal_min": 180.0,
                "kcal_max": 260.0,
                "kcal_source": "estimated",
                "source_note": "参考食物库",
            }
        ],
        "weight_measurements": [
            {"measured_at": f"{date}T07:00:00", "weight_kg": 49.5,
             "condition": "morning_fasted_after_urination"}
        ],
    }


class TestFoodEntriesKeepCalories:
    def test_kcal_fields_survive_restore(self, client):
        http, engine = client
        resp = _post_backup(http, [_sample_record()])
        assert resp.status_code == 200
        assert resp.json()["restored"] == 1

        with Session(engine) as s:
            fe = s.exec(select(FoodEntry)).one()
            assert fe.kcal == 220.0
            assert fe.kcal_min == 180.0
            assert fe.kcal_max == 260.0
            assert fe.quantity_g == 120.0
            assert fe.source_note == "参考食物库"


class TestNoFabricatedWeights:
    def test_zero_and_missing_weights_are_skipped(self, client):
        http, engine = client
        rec = _sample_record("2026-08-02")
        rec["weight_measurements"] = [
            {"measured_at": "2026-08-02T07:00:00"},                # missing weight_kg
            {"measured_at": "2026-08-02T08:00:00", "weight_kg": 0},  # zero
            {"measured_at": "2026-08-02T09:00:00", "weight_kg": True},  # bool trap
        ]
        resp = _post_backup(http, [rec])
        assert resp.status_code == 200
        assert resp.json()["restored"] == 1  # record itself is fine

        with Session(engine) as s:
            weights = s.exec(select(WeightMeasurement)).all()
            assert weights == []  # nothing fabricated


class TestAtomicPerRecord:
    def test_failed_record_leaves_no_partial_data(self, client):
        http, engine = client
        bad = _sample_record("2026-08-03")
        bad["food_entries"] = ["not-a-dict"]  # triggers mid-record failure
        good = _sample_record("2026-08-04")

        resp = _post_backup(http, [bad, good])
        assert resp.status_code == 200
        body = resp.json()
        assert body["errors"] == 1
        assert body["restored"] == 1

        with Session(engine) as s:
            # The bad record must not exist at all (no half-written record)
            assert s.exec(
                select(DailyRecord).where(DailyRecord.record_date == "2026-08-03")
            ).first() is None
            # The good record restored fully, unaffected by the bad one
            good_rec = s.exec(
                select(DailyRecord).where(DailyRecord.record_date == "2026-08-04")
            ).one()
            foods = s.exec(
                select(FoodEntry).where(FoodEntry.daily_record_id == good_rec.id)
            ).all()
            assert len(foods) == 1
            assert foods[0].kcal == 220.0


class TestExistingDatesSkipped:
    def test_existing_record_not_overwritten(self, client):
        http, engine = client
        assert _post_backup(http, [_sample_record("2026-08-05")]).json()["restored"] == 1

        modified = _sample_record("2026-08-05")
        modified["weight_kg"] = 99.9
        resp = _post_backup(http, [modified])
        assert resp.json()["skipped"] == 1

        with Session(engine) as s:
            rec = s.exec(
                select(DailyRecord).where(DailyRecord.record_date == "2026-08-05")
            ).one()
            assert rec.weight_kg == 49.5  # untouched


class TestDryRun:
    def test_dry_run_writes_nothing(self, client):
        http, engine = client
        resp = _post_backup(http, [_sample_record("2026-08-06")], dry_run=True)
        assert resp.json()["restored"] == 1  # would-restore count

        with Session(engine) as s:
            assert s.exec(select(DailyRecord)).all() == []
