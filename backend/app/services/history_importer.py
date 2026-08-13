"""Idempotent importer for historical records.

Guarantees (per CODEX_MASTER_PROMPT / PRD / 导入规则 sheet):
  * Originals are only READ (seed/ copy is already read-only, chmod 444).
  * Import is idempotent: a date already present is SKIPPED, never overwritten.
  * Imported daily records are locked (is_locked = 1).
  * Every import batch writes an audit_log entry.
  * Estimated calories keep min/max + data_status; nothing is faked as exact.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from app.models import DailyRecord, FoodEntry, WeightMeasurement, AuditLog
from app.schemas import ImportResult

# history_importer.py lives in backend/app/services -> go up 3 levels to backend/
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SEED_DIR = os.path.join(
    sys._MEIPASS if getattr(sys, "frozen", False) else BACKEND_DIR,
    "seed",
)

DRINK_KEYWORDS = ("咖啡", "美式", "拿铁", "茶", "可乐", "饮", "冰萃",
                  "水溶", "果汁", "牛奶", "奶茶", "啤酒", "酒", "酸奶")

MEAL_FIELDS = ("breakfast", "lunch", "snacks_drinks", "dinner")


def _default_seed(format: str) -> str:
    return os.path.join(SEED_DIR, f"historical_records.{format}")


def _derive_period(status: Optional[str]):
    if not status:
        return (None, None)
    if "or" in status:  # ambiguous e.g. period_day_5_or_6
        return (None, None)
    pd = pu = None
    m = re.search(r"period_day_(\d+)", status)
    if m:
        pd = int(m.group(1))
    m = re.search(r"pre_period_(\d+)_days", status)
    if m:
        pu = int(m.group(1))
    return (pd, pu)


def _split_meal(text: Optional[str]) -> List[str]:
    if not text:
        return []
    parts = re.split(r"[；;]|\n", text)
    return [p.strip() for p in parts if p.strip()]


def _is_drink(item: str) -> bool:
    return any(k in item for k in DRINK_KEYWORDS)


def _normalize_json(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "date": raw.get("date"),
        "weight_kg": raw.get("weight_kg"),
        "bowel_movement": raw.get("bowel_movement", "unknown"),
        "period_status": raw.get("period_status"),
        "breakfast": raw.get("breakfast"),
        "lunch": raw.get("lunch"),
        "snacks_drinks": raw.get("snacks_drinks"),
        "dinner": raw.get("dinner"),
        "kcal_min": raw.get("estimated_kcal_min"),
        "kcal_max": raw.get("estimated_kcal_max"),
        "analysis": raw.get("analysis"),
        "data_status": raw.get("data_status", "estimated"),
        "notes": raw.get("notes"),
    }


def _normalize_csv(row: Dict[str, str]) -> Dict[str, Any]:
    def num(v):
        v = (v or "").strip()
        return float(v) if v not in ("", "None", "null") else None
    return {
        "date": row.get("date"),
        "weight_kg": num(row.get("weight_kg")),
        "bowel_movement": row.get("bowel_movement") or "unknown",
        "period_status": row.get("period_status") or None,
        "breakfast": row.get("breakfast") or None,
        "lunch": row.get("lunch") or None,
        "snacks_drinks": row.get("snacks_drinks") or None,
        "dinner": row.get("dinner") or None,
        "kcal_min": num(row.get("estimated_kcal_min")),
        "kcal_max": num(row.get("estimated_kcal_max")),
        "analysis": row.get("analysis") or None,
        "data_status": row.get("data_status") or "estimated",
        "notes": row.get("notes") or None,
    }


def _load_records(format: str, path: Optional[str]) -> List[Dict[str, Any]]:
    path = path or _default_seed(format)
    if format == "json":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [_normalize_json(r) for r in data]
    elif format == "csv":
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = []
            for row in reader:
                clean = {k.lstrip("\ufeff"): v for k, v in row.items()}
                rows.append(_normalize_csv(clean))
            return rows
    else:
        raise ValueError(f"unsupported format: {format}")


def _cross_check_csv(records: List[Dict[str, Any]], details: List[Dict[str, Any]]):
    """Warn (non-fatal) when CSV date set differs from JSON source set."""
    try:
        csv_path = _default_seed("csv")
        if not os.path.exists(csv_path):
            return
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            csv_dates = set()
            for r in reader:
                clean = {k.lstrip("\ufeff"): v for k, v in r.items()}
                if clean.get("date"):
                    csv_dates.add(clean["date"])
        json_dates = {r["date"] for r in records}
        missing = json_dates - csv_dates
        extra = csv_dates - json_dates
        if missing:
            details.append({"level": "warning", "message": f"CSV 缺少 JSON 中的日期: {sorted(missing)}"})
        if extra:
            details.append({"level": "warning", "message": f"CSV 多出 JSON 没有的日期: {sorted(extra)}"})
    except Exception as e:  # never block import on cross-check failure
        details.append({"level": "warning", "message": f"CSV 交叉校验跳过: {e}"})


def _process_record(session: Session, rec: Dict[str, Any], dry_run: bool) -> str:
    date = rec.get("date")
    if not date or not re.match(r"^\d{4}-\d{2}-\d{2}$", str(date)):
        raise ValueError(f"无效日期: {date!r}")

    existing = session.exec(
        select(DailyRecord).where(DailyRecord.record_date == date)
    ).first()
    if existing is not None:
        return "skipped"  # locked record is never overwritten

    if dry_run:
        return "inserted"  # would-be insert

    pd, pu = _derive_period(rec.get("period_status"))
    record = DailyRecord(
        record_date=date,
        weight_kg=rec.get("weight_kg"),
        bowel_movement=rec.get("bowel_movement") or "unknown",
        period_status=rec.get("period_status"),
        period_day=pd,
        period_days_until=pu,
        total_kcal_min=rec.get("kcal_min"),
        total_kcal_max=rec.get("kcal_max"),
        total_kcal_confirmed=None,  # history has only ranges, no single confirmed value
        analysis=rec.get("analysis"),
        notes=rec.get("notes"),
        data_status=rec.get("data_status") or "estimated",
        raw_input=json.dumps(rec, ensure_ascii=False),
        source="history_import",
        is_locked=1,
    )
    session.add(record)
    session.flush()  # populate record.id

    sort = 0
    for field in MEAL_FIELDS:
        text = rec.get(field)
        for item in _split_meal(text):
            if field == "snacks_drinks":
                meal_type = "drink" if _is_drink(item) else "snack"
            else:
                meal_type = field
            session.add(FoodEntry(
                daily_record_id=record.id,
                meal_type=meal_type,
                food_name=item[:200],
                quantity_text=item,
                kcal_source="estimated",
                sort_order=sort,
            ))
            sort += 1

    if rec.get("weight_kg") is not None:
        session.add(WeightMeasurement(
            measured_at=f"{date}T07:00:00",
            weight_kg=rec["weight_kg"],
            condition="morning_fasted_after_urination",
            daily_record_id=record.id,
        ))
    session.commit()
    return "inserted"


def import_history(session: Session, format: str = "json",
                   dry_run: bool = False, path: Optional[str] = None) -> ImportResult:
    records = _load_records(format, path)
    details: List[Dict[str, Any]] = []

    if format == "json":
        _cross_check_csv(records, details)

    result = ImportResult(dry_run=dry_run, source=format)
    seen = set()
    for rec in records:
        date = rec.get("date")
        if date in seen:
            details.append({"date": date, "status": "duplicate_in_file"})
            result.skipped += 1
            continue
        seen.add(date)
        try:
            status = _process_record(session, rec, dry_run)
        except Exception as e:
            details.append({"date": date, "status": "error", "message": str(e)})
            result.errors += 1
            continue
        if status == "inserted":
            result.inserted += 1
            details.append({"date": date, "status": "inserted"})
        else:
            result.skipped += 1
            details.append({"date": date, "status": "skipped"})

    result.details = details

    if not dry_run:
        session.add(AuditLog(
            entity_type="import_batch",
            entity_id=None,
            action="import_history",
            before_json=None,
            after_json=json.dumps(
                {"inserted": result.inserted, "skipped": result.skipped,
                 "errors": result.errors, "source": format},
                ensure_ascii=False,
            ),
        ))
        session.commit()

    return result
