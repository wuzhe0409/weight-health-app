"""Pydantic request/response schemas."""
from __future__ import annotations

from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel


class FoodEntryCreate(SQLModel):
    meal_type: str
    food_name: str
    quantity_text: Optional[str] = None
    quantity_g: Optional[float] = None
    kcal: Optional[float] = None
    kcal_min: Optional[float] = None
    kcal_max: Optional[float] = None
    kcal_source: str = "estimated"
    source_note: Optional[str] = None
    sort_order: int = 0


class RecordCreate(SQLModel):
    record_date: str
    weight_kg: Optional[float] = None
    bowel_movement: str = "unknown"
    period_status: Optional[str] = None
    period_day: Optional[int] = None
    period_days_until: Optional[int] = None
    total_kcal_min: Optional[float] = None
    total_kcal_max: Optional[float] = None
    total_kcal_confirmed: Optional[float] = None
    protein_g: Optional[float] = None
    analysis: Optional[str] = None
    notes: Optional[str] = None
    data_status: str = "estimated"
    raw_input: Optional[str] = None
    food_entries: List[FoodEntryCreate] = []


class ParsePreview(SQLModel):
    record_date: Optional[str] = None
    weight_kg: Optional[float] = None
    bowel_movement: Optional[str] = None
    period_status: Optional[str] = None
    period_day: Optional[int] = None
    period_days_until: Optional[int] = None
    meals: Dict[str, List[str]] = {}
    raw_text: str = ""
    note: str = "本地规则解析结果，请确认后再保存。"


class ImportResult(SQLModel):
    inserted: int = 0
    skipped: int = 0
    errors: int = 0
    details: List[Dict[str, Any]] = []
    dry_run: bool = False
    source: str = ""


class RecordResponse(SQLModel):
    id: int
    record_date: str
    weight_kg: Optional[float] = None
    bowel_movement: str = "unknown"
    period_status: Optional[str] = None
    period_day: Optional[int] = None
    period_days_until: Optional[int] = None
    total_kcal_min: Optional[float] = None
    total_kcal_max: Optional[float] = None
    total_kcal_confirmed: Optional[float] = None
    analysis: Optional[str] = None
    notes: Optional[str] = None
    data_status: str = "estimated"
    raw_input: Optional[str] = None
    source: str = "manual_or_ai"
    is_locked: int = 0
    food_entries: List[Dict[str, Any]] = []
    weight_measurements: List[Dict[str, Any]] = []


# ── Food Library ──
class FoodLibraryCreate(SQLModel):
    name: str
    category: str = "other"
    calories_per_100g: Optional[float] = None
    protein_per_100g: Optional[float] = None
    carbs_per_100g: Optional[float] = None
    fat_per_100g: Optional[float] = None
    common_portion: Optional[str] = None
    common_portion_g: Optional[float] = None
    common_portion_kcal: Optional[float] = None


class FoodLibraryResponse(SQLModel):
    id: int
    name: str
    category: str = "other"
    calories_per_100g: Optional[float] = None
    protein_per_100g: Optional[float] = None
    carbs_per_100g: Optional[float] = None
    fat_per_100g: Optional[float] = None
    common_portion: Optional[str] = None
    common_portion_g: Optional[float] = None
    common_portion_kcal: Optional[float] = None
    is_custom: int = 0


class FoodSearchResult(SQLModel):
    items: List[FoodLibraryResponse] = []
    total: int = 0
