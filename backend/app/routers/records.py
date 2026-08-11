"""Records API: parse (preview), save, query, detail, revision, batch-fill."""
from __future__ import annotations

import json
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import DailyRecord, FoodEntry, AuditLog
from app.schemas import RecordCreate, ParsePreview, BatchFillItem, BatchFillResult
from app.serialize import record_to_dict, records_to_dicts
from app.services.ai_provider import get_provider

router = APIRouter(prefix="/api/records", tags=["records"])


@router.post("/parse", response_model=ParsePreview)
def parse_text(payload: dict):
    """Parse natural-language text into a preview. Does NOT save."""
    text = payload.get("text", "")
    rd = payload.get("record_date")
    base = date.fromisoformat(rd) if rd else None
    provider = get_provider(payload.get("provider", "local"))
    return provider.parse(text, base)


def _apply_record(session: Session, data: RecordCreate) -> DailyRecord:
    rec = session.exec(
        select(DailyRecord).where(DailyRecord.record_date == data.record_date)
    ).first()

    if rec is None:
        rec = DailyRecord(record_date=data.record_date)
        session.add(rec)
        session.flush()
    # replace food entries
    old_foods = session.exec(
        select(FoodEntry).where(FoodEntry.daily_record_id == rec.id)
    ).all()
    for f in old_foods:
        session.delete(f)
    session.flush()

    rec.weight_kg = data.weight_kg
    rec.bowel_movement = data.bowel_movement
    rec.period_status = data.period_status
    rec.period_day = data.period_day
    rec.period_days_until = data.period_days_until
    rec.total_kcal_min = data.total_kcal_min
    rec.total_kcal_max = data.total_kcal_max
    rec.total_kcal_confirmed = data.total_kcal_confirmed
    rec.protein_g = data.protein_g
    rec.analysis = data.analysis
    rec.notes = data.notes
    rec.data_status = data.data_status
    rec.raw_input = data.raw_input

    for i, fe in enumerate(data.food_entries):
        session.add(FoodEntry(
            daily_record_id=rec.id,
            meal_type=fe.meal_type,
            food_name=fe.food_name,
            quantity_text=fe.quantity_text,
            quantity_g=fe.quantity_g,
            kcal=fe.kcal,
            kcal_min=fe.kcal_min,
            kcal_max=fe.kcal_max,
            kcal_source=fe.kcal_source,
            source_note=fe.source_note,
            sort_order=i,
        ))
    session.commit()
    session.refresh(rec)
    return rec


@router.post("", response_model=dict)
def save_record(data: RecordCreate, session: Session = Depends(get_session)):
    existing = session.exec(
        select(DailyRecord).where(DailyRecord.record_date == data.record_date)
    ).first()
    if existing is not None and existing.is_locked == 1:
        raise HTTPException(
            status_code=409,
            detail="该日期为锁定历史记录，不能直接覆盖。请使用修订接口 /revisions。",
        )
    rec = _apply_record(session, data)
    return record_to_dict(rec, session)


@router.get("", response_model=list)
def list_records(
    start: Optional[str] = None,
    end: Optional[str] = None,
    session: Session = Depends(get_session),
):
    stmt = select(DailyRecord)
    if start:
        stmt = stmt.where(DailyRecord.record_date >= start)
    if end:
        stmt = stmt.where(DailyRecord.record_date <= end)
    stmt = stmt.order_by(DailyRecord.record_date)
    records = session.exec(stmt).all()
    return records_to_dicts(records, session)


@router.get("/{record_date}", response_model=dict)
def get_record(record_date: str, session: Session = Depends(get_session)):
    rec = session.exec(
        select(DailyRecord).where(DailyRecord.record_date == record_date)
    ).first()
    if rec is None:
        raise HTTPException(status_code=404, detail="未找到该日期记录")
    return record_to_dict(rec, session)


@router.post("/{record_date}/revisions", response_model=dict)
def add_revision(record_date: str, data: RecordCreate, session: Session = Depends(get_session)):
    """Add a revision to an existing (possibly locked) record without destroying
    the original: the previous state is written to audit_log, raw_input preserved."""
    rec = session.exec(
        select(DailyRecord).where(DailyRecord.record_date == record_date)
    ).first()
    if rec is None:
        raise HTTPException(status_code=404, detail="未找到该日期记录")

    before = json.dumps(record_to_dict(rec, session), ensure_ascii=False, default=str)
    # preserve original natural-language input
    original_raw = rec.raw_input
    rec = _apply_record(session, data)
    rec.raw_input = original_raw  # do not overwrite the original raw text
    session.commit()
    session.refresh(rec)

    after = json.dumps(record_to_dict(rec, session), ensure_ascii=False, default=str)
    session.add(AuditLog(
        entity_type="daily_record",
        entity_id=rec.id,
        action="revision",
        before_json=before,
        after_json=after,
    ))
    session.commit()
    return record_to_dict(rec, session)


@router.post("/exists", response_model=dict)
def batch_exists(dates: List[str], session: Session = Depends(get_session)):
    """Check which dates already have records. One query instead of N round-trips."""
    if len(dates) > 90:
        raise HTTPException(status_code=422, detail="too many dates (max 90)")
    found = session.exec(
        select(DailyRecord.record_date).where(DailyRecord.record_date.in_(dates))
    ).all()
    return {"existing": sorted(found)}


@router.post("/batch-fill", response_model=BatchFillResult)
def batch_fill(items: List[BatchFillItem], session: Session = Depends(get_session)):
    """Bulk fill weight/bowel data for multiple dates.

    For each date:
    - If no record exists → create one with the given fields.
    - If a record exists and is NOT locked → update weight & bowel (preserve other fields).
    - If a record exists and IS locked → skip it (return as skipped).
    """
    results: List[dict] = []
    updated = 0
    created = 0
    skipped = 0

    for item in items:
        rec = session.exec(
            select(DailyRecord).where(DailyRecord.record_date == item.record_date)
        ).first()

        action = ""
        if rec is None:
            rec = DailyRecord(
                record_date=item.record_date,
                weight_kg=item.weight_kg,
                bowel_movement=item.bowel_movement,
                data_status="estimated",
            )
            session.add(rec)
            action = "created"
            created += 1
        elif rec.is_locked == 1:
            action = "skipped"
            skipped += 1
        else:
            # Only overwrite fields if caller provides non-null / non-default values
            if item.weight_kg is not None:
                rec.weight_kg = item.weight_kg
            if item.bowel_movement and item.bowel_movement != "unknown":
                rec.bowel_movement = item.bowel_movement
            action = "updated"
            updated += 1

        session.flush()
        results.append({
            "record_date": item.record_date,
            "weight_kg": rec.weight_kg,
            "bowel_movement": rec.bowel_movement if action != "skipped" else rec.bowel_movement,
            "action": action,
        })

    session.commit()
    return BatchFillResult(
        items=results,
        total_created=created,
        total_updated=updated,
        total_skipped=skipped,
    )
