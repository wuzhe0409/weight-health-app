"""Tests for date-window avg7 and NL time-adverb disambiguation.

Covers two logic fixes (2026-08-21):
  1. weight_trend avg7 must use a DATE window (today-6..today), so recording
     gaps don't pull stale weights into "recent 7-day" averages.
  2. nlp_parser must not treat time adverbs (晚上/中午/上午/下午) as meal
     markers unless the following segment is about eating/drinking.
"""
import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine, select

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import get_session
from app.main import app
from app.models import DailyRecord
from app.services.nlp_parser import parse_text


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


def _add_weight(engine, day: str, kg: float):
    with Session(engine) as s:
        s.add(DailyRecord(record_date=day, weight_kg=kg))
        s.commit()


class TestAvg7DateWindow:
    def test_gap_does_not_leak_stale_weight(self, client):
        http, engine = client
        # 7 consecutive days, then a 20-day gap, then one more record.
        for i in range(7):
            _add_weight(engine, f"2026-07-{1 + i:02d}", 50.0)
        _add_weight(engine, "2026-07-27", 48.0)

        data = http.get("/api/stats/weight-trend").json()
        last = data[-1]
        assert last["record_date"] == "2026-07-27"
        # Date window contains ONLY 07-27 — old 50.0 values must not leak in.
        assert last["avg7"] == 48.0

    def test_normal_week_averages_all_days(self, client):
        http, engine = client
        weights = [49.0, 49.2, 49.4, 49.3, 49.1, 49.0, 48.9]
        for i, w in enumerate(weights):
            _add_weight(engine, f"2026-08-{1 + i:02d}", w)

        data = http.get("/api/stats/weight-trend").json()
        last = data[-1]
        assert last["avg7"] == round(sum(weights) / 7, 2)

    def test_window_slides_by_date(self, client):
        http, engine = client
        # 8 days of 50.0, then a 49.0 — window should hold the last 7 days
        # (drop day 1), average = (50*7 + 49)/8? No: last 7 = 6*50 + 49.
        for i in range(8):
            _add_weight(engine, f"2026-08-{1 + i:02d}", 50.0)
        _add_weight(engine, "2026-08-09", 49.0)

        data = http.get("/api/stats/weight-trend").json()
        last = data[-1]
        expected = round((50.0 * 6 + 49.0) / 7, 2)
        assert last["avg7"] == expected


class TestTimeAdverbNotMeal:
    def test_weighing_note_not_dinner(self):
        preview = parse_text("我晚上称的体重49.5 早餐吃了包子")
        assert preview.weight_kg == 49.5
        dinner = preview.meals.get("dinner", [])
        assert not any("称" in item or "体重" in item for item in dinner)
        assert preview.meals.get("breakfast") == ["吃了包子"]

    def test_evening_meal_still_works(self):
        preview = parse_text("晚上吃了麻辣烫")
        assert preview.meals.get("dinner") == ["吃了麻辣烫"]

    def test_evening_skipped_meal_still_works(self):
        preview = parse_text("晚上没吃")
        assert preview.meals.get("dinner") == ["没吃"]

    def test_noon_adverb_without_eating_skipped(self):
        preview = parse_text("中午睡了半小时 早餐吃了鸡蛋")
        lunch = preview.meals.get("lunch", [])
        assert not any("睡" in item for item in lunch)
        assert preview.meals.get("breakfast") == ["吃了鸡蛋"]
