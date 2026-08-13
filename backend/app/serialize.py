"""Shared serialization helpers."""
from __future__ import annotations

from typing import List

from sqlmodel import Session, select

from app.models import DailyRecord, FoodEntry, WeightMeasurement


def record_to_dict(record: DailyRecord, session: Session) -> dict:
    foods = session.exec(
        select(FoodEntry)
        .where(FoodEntry.daily_record_id == record.id)
        .order_by(FoodEntry.sort_order)
    ).all()
    weights = session.exec(
        select(WeightMeasurement)
        .where(WeightMeasurement.daily_record_id == record.id)
        .order_by(WeightMeasurement.measured_at)
    ).all()
    return _build_dict(record, foods, weights)


def records_to_dicts(records: List[DailyRecord], session: Session) -> List[dict]:
    """Serialize many records with only 2 queries total (no N+1)."""
    ids = [r.id for r in records]
    if not ids:
        return []
    all_foods = session.exec(
        select(FoodEntry)
        .where(FoodEntry.daily_record_id.in_(ids))
        .order_by(FoodEntry.sort_order)
    ).all()
    all_weights = session.exec(
        select(WeightMeasurement)
        .where(WeightMeasurement.daily_record_id.in_(ids))
        .order_by(WeightMeasurement.measured_at)
    ).all()
    foods_by_id: dict = {}
    for f in all_foods:
        foods_by_id.setdefault(f.daily_record_id, []).append(f)
    weights_by_id: dict = {}
    for w in all_weights:
        weights_by_id.setdefault(w.daily_record_id, []).append(w)
    return [
        _build_dict(r, foods_by_id.get(r.id, []), weights_by_id.get(r.id, []))
        for r in records
    ]


def _build_dict(record: DailyRecord, foods, weights) -> dict:
    return {
        "id": record.id,
        "record_date": record.record_date,
        "weight_kg": record.weight_kg,
        "bowel_movement": record.bowel_movement,
        "period_status": record.period_status,
        "period_day": record.period_day,
        "period_days_until": record.period_days_until,
        "total_kcal_min": record.total_kcal_min,
        "total_kcal_max": record.total_kcal_max,
        "total_kcal_confirmed": record.total_kcal_confirmed,
        "protein_g": record.protein_g,
        "steps": record.steps,
        "water_ml": record.water_ml,
        "analysis": record.analysis,
        "notes": record.notes,
        "data_status": record.data_status,
        "raw_input": record.raw_input,
        "source": record.source,
        "is_locked": record.is_locked,
        "food_entries": [f.model_dump() for f in foods],
        "weight_measurements": [w.model_dump() for w in weights],
    }
