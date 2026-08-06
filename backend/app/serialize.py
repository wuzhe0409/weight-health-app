"""Shared serialization helpers."""
from __future__ import annotations

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
