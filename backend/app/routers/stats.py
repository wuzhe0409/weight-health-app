"""Statistics API: weight trend, calories, cycle analysis, food search."""
from __future__ import annotations

from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func, or_

from app.db import get_session
from app.models import DailyRecord, FoodEntry, WeightMeasurement

router = APIRouter(prefix="/api/stats", tags=["stats"])


def _period_category(status: Optional[str]) -> str:
    if not status:
        return "unknown"
    if status.startswith("pre_period"):
        return "pre"
    if status == "period" or status.startswith("period_day"):
        return "period"
    if status in ("post_period", "period_ended", "period_ended_or_late_period"):
        return "post"
    return "unknown"


@router.get("/weight-trend")
def weight_trend(start: Optional[str] = None, end: Optional[str] = None,
                 session: Session = Depends(get_session)):
    stmt = select(DailyRecord).where(DailyRecord.weight_kg.is_not(None))
    if start:
        stmt = stmt.where(DailyRecord.record_date >= start)
    if end:
        stmt = stmt.where(DailyRecord.record_date <= end)
    stmt = stmt.order_by(DailyRecord.record_date)
    records = session.exec(stmt).all()

    window: list[float] = []
    out = []
    for r in records:
        window.append(r.weight_kg)
        if len(window) > 7:
            window.pop(0)
        avg7 = round(sum(window) / len(window), 2) if window else None
        out.append({
            "record_date": r.record_date,
            "weight_kg": r.weight_kg,
            "avg7": avg7,
            "bowel_movement": r.bowel_movement,
            "period_status": r.period_status,
            "is_locked": r.is_locked,
        })
    return out


@router.get("/calories")
def calories(start: Optional[str] = None, end: Optional[str] = None,
             session: Session = Depends(get_session)):
    stmt = select(DailyRecord).where(
        DailyRecord.total_kcal_min.is_not(None) | DailyRecord.total_kcal_max.is_not(None)
    )
    if start:
        stmt = stmt.where(DailyRecord.record_date >= start)
    if end:
        stmt = stmt.where(DailyRecord.record_date <= end)
    stmt = stmt.order_by(DailyRecord.record_date)
    records = session.exec(stmt).all()
    return [{
        "record_date": r.record_date,
        "total_kcal_min": r.total_kcal_min,
        "total_kcal_max": r.total_kcal_max,
        "total_kcal_confirmed": r.total_kcal_confirmed,
        "data_status": r.data_status,
    } for r in records]


@router.get("/cycle")
def cycle_stats(session: Session = Depends(get_session)):
    records = session.exec(select(DailyRecord)).all()
    by_cat: dict[str, list[float]] = defaultdict(list)
    no_bowel_weights: list[float] = []
    all_weights: list[float] = []
    for r in records:
        if r.weight_kg is None:
            continue
        all_weights.append(r.weight_kg)
        by_cat[_period_category(r.period_status)].append(r.weight_kg)
        if r.bowel_movement == "previous_day_no":
            no_bowel_weights.append(r.weight_kg)

    def avg(xs):
        return round(sum(xs) / len(xs), 2) if xs else None

    overall = avg(all_weights)
    result = {
        "overall_avg_weight": overall,
        "avg_weight_by_phase": {k: avg(v) for k, v in by_cat.items()},
        "avg_weight_after_no_bowel_day": avg(no_bowel_weights),
        "no_bowel_sample_size": len(no_bowel_weights),
    }
    if result["avg_weight_after_no_bowel_day"] is not None and overall is not None:
        result["no_bowel_vs_overall_delta"] = round(
            result["avg_weight_after_no_bowel_day"] - overall, 2
        )
    pre = result["avg_weight_by_phase"].get("pre")
    post = result["avg_weight_by_phase"].get("post")
    if pre is not None and post is not None:
        result["pre_minus_post_delta"] = round(pre - post, 2)
    return result


@router.get("/search")
def search_food(keyword: str = Query(..., min_length=1),
                session: Session = Depends(get_session)):
    kw = f"%{keyword}%"
    stmt = (
        select(FoodEntry, DailyRecord.record_date)
        .join(DailyRecord, FoodEntry.daily_record_id == DailyRecord.id)
        .where(or_(FoodEntry.food_name.like(kw), FoodEntry.quantity_text.like(kw)))
        .order_by(DailyRecord.record_date)
    )
    rows = session.exec(stmt).all()
    return [{
        "record_date": rd,
        "meal_type": fe.meal_type,
        "food_name": fe.food_name,
        "quantity_text": fe.quantity_text,
        "kcal_source": fe.kcal_source,
    } for fe, rd in rows]
