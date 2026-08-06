"""Import history (idempotent) and export all data."""
from __future__ import annotations

import csv
import io
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, JSONResponse
from sqlmodel import Session, select

from app.db import get_session
from app.models import DailyRecord
from app.serialize import record_to_dict
from app.services.history_importer import import_history

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
