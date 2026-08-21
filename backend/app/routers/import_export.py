"""Import history (idempotent) and export all data."""
from __future__ import annotations

import csv
import io
import json
import re
from datetime import date as _date

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import Response, JSONResponse
from sqlmodel import Session, select

from app.db import get_session
from app.models import DailyRecord, FoodEntry, WeightMeasurement, AuditLog
from app.serialize import record_to_dict
from app.services.history_importer import import_history

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _is_valid_date(s: str) -> bool:
    """YYYY-MM-DD format AND real calendar date (rejects 2026-13-99 etc.)."""
    if not DATE_PATTERN.match(s):
        return False
    try:
        _date.fromisoformat(s)
        return True
    except ValueError:
        return False

router = APIRouter(tags=["import_export"])


@router.post("/api/import/history")
def import_history_endpoint(
    format: str = "json",
    dry_run: bool = False,
    session: Session = Depends(get_session),
):
    if format not in ("json", "csv"):
        raise HTTPException(status_code=400, detail="format must be json or csv")
    return import_history(session, format=format, dry_run=dry_run)


@router.get("/api/export")
def export_data(format: str = "json", session: Session = Depends(get_session)):
    records = session.exec(select(DailyRecord).order_by(DailyRecord.record_date)).all()
    data = [record_to_dict(r, session) for r in records]
    if format == "json":
        return JSONResponse(content=data)
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "date", "weight_kg", "bowel_movement", "period_status", "period_day",
            "period_days_until", "total_kcal_min", "total_kcal_max", "total_kcal_confirmed",
            "data_status", "source", "is_locked", "notes", "food_entries",
        ])
        for r in data:
            foods = "; ".join(f"[{f['meal_type']}] {f['food_name']}" for f in r["food_entries"])
            writer.writerow([
                r["record_date"], r["weight_kg"], r["bowel_movement"], r["period_status"],
                r["period_day"], r["period_days_until"], r["total_kcal_min"], r["total_kcal_max"],
                r["total_kcal_confirmed"], r["data_status"], r["source"], r["is_locked"],
                r["notes"], foods,
            ])
        return Response(content=output.getvalue(), media_type="text/csv")
    raise HTTPException(status_code=400, detail="format must be json or csv")


@router.post("/api/import/backup")
async def import_backup_endpoint(
    file: UploadFile = File(...),
    dry_run: bool = False,
    session: Session = Depends(get_session),
):
    """Restore from a JSON backup file exported by /api/export.

    Behaviour:
    - Skips records whose record_date already exists in DB (no overwrite of
      data the user has manually edited after the backup was made).
    - Recreates the missing record plus its nested food_entries and
      weight_measurements arrays.
    - If dry_run=true, reports what would be restored without writing.

    Returns: {"dry_run": bool, "restored": N, "skipped": M, "errors": K, "details": [...]}
    """
    if not file.filename or not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json backup files are supported")

    raw = await file.read()
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="Backup file must be a JSON array of records")

    result = {
        "dry_run": dry_run,
        "restored": 0,
        "skipped": 0,
        "errors": 0,
        "details": [],
    }

    for rec in data:
        if not isinstance(rec, dict):
            result["errors"] += 1
            result["details"].append({
                "record_date": None,
                "status": "error",
                "message": f"each item must be an object, got {type(rec).__name__}",
            })
            continue
        date = rec.get("record_date")
        if not date or not isinstance(date, str) or not _is_valid_date(date):
            result["errors"] += 1
            result["details"].append({
                "record_date": date,
                "status": "error",
                "message": "missing or invalid date format (expected YYYY-MM-DD with real calendar date)",
            })
            continue

        existing = session.exec(
            select(DailyRecord).where(DailyRecord.record_date == date)
        ).first()
        if existing is not None:
            result["skipped"] += 1
            result["details"].append({"record_date": date, "status": "skipped", "message": "already exists"})
            continue

        if dry_run:
            result["restored"] += 1
            result["details"].append({"record_date": date, "status": "would_restore"})
            continue

        # SAVEPOINT per record: a failure mid-record must roll back THAT
        # record only — never commit a half-written record (record without
        # its food entries) as part of the batch.
        try:
            with session.begin_nested():
                new_rec = DailyRecord(
                    record_date=date,
                    weight_kg=rec.get("weight_kg"),
                    bowel_movement=rec.get("bowel_movement", "unknown"),
                    period_status=rec.get("period_status"),
                    period_day=rec.get("period_day"),
                    period_days_until=rec.get("period_days_until"),
                    total_kcal_min=rec.get("total_kcal_min"),
                    total_kcal_max=rec.get("total_kcal_max"),
                    total_kcal_confirmed=rec.get("total_kcal_confirmed"),
                    protein_g=rec.get("protein_g"),
                    steps=rec.get("steps"),
                    water_ml=rec.get("water_ml"),
                    analysis=rec.get("analysis"),
                    notes=rec.get("notes"),
                    data_status=rec.get("data_status", "estimated"),
                    raw_input=rec.get("raw_input"),
                    source=rec.get("source") or "backup_restore",
                    is_locked=rec.get("is_locked", 0),
                )
                session.add(new_rec)
                session.flush()

                for idx, f in enumerate(rec.get("food_entries", []) or []):
                    if not isinstance(f, dict):
                        raise ValueError(f"food_entries[{idx}] must be an object")
                    session.add(FoodEntry(
                        daily_record_id=new_rec.id,
                        meal_type=f.get("meal_type", "snack"),
                        food_name=f.get("food_name", ""),
                        quantity_text=f.get("quantity_text", ""),
                        quantity_g=f.get("quantity_g"),
                        kcal=f.get("kcal"),
                        kcal_min=f.get("kcal_min"),
                        kcal_max=f.get("kcal_max"),
                        kcal_source=f.get("kcal_source", "estimated"),
                        source_note=f.get("source_note"),
                        sort_order=idx,
                    ))

                for w in rec.get("weight_measurements", []) or []:
                    if not isinstance(w, dict):
                        raise ValueError("weight_measurements items must be objects")
                    wkg = w.get("weight_kg")
                    # Never fabricate a 0kg measurement — skip incomplete entries.
                    if not isinstance(wkg, (int, float)) or isinstance(wkg, bool) or wkg <= 0:
                        continue
                    session.add(WeightMeasurement(
                        measured_at=w.get("measured_at") or f"{date}T07:00:00",
                        weight_kg=wkg,
                        condition=w.get("condition", "morning_fasted_after_urination"),
                        daily_record_id=new_rec.id,
                    ))

            result["restored"] += 1
            result["details"].append({"record_date": date, "status": "restored"})
        except Exception as e:
            result["errors"] += 1
            result["details"].append({"record_date": date, "status": "error", "message": str(e)})

    if not dry_run:
        session.add(AuditLog(
            entity_type="import_batch",
            entity_id=None,
            action="import_backup",
            before_json=None,
            after_json=json.dumps(
                {"restored": result["restored"], "skipped": result["skipped"],
                 "errors": result["errors"]},
                ensure_ascii=False,
            ),
        ))
        session.commit()

    return result
