"""SQLModel tables mirroring schema.sql."""
from __future__ import annotations

from datetime import datetime
from sqlmodel import SQLModel, Field


class UserProfile(SQLModel, table=True):
    __tablename__ = "user_profile"
    id: int = Field(default=1, primary_key=True)
    gender: str = Field(default="female")
    age: int | None = None
    height_cm: float | None = None
    frame_size: str | None = None
    target_weight_kg: float | None = None
    bmr_formula: str = Field(default="Mifflin-St Jeor")
    llm_provider: str | None = Field(default="deepseek")
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    # Vision model for food image analysis (e.g. GLM-4V)
    vision_api_key: str | None = None
    vision_base_url: str | None = None
    vision_model: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


class DailyRecord(SQLModel, table=True):
    __tablename__ = "daily_records"
    id: int | None = Field(default=None, primary_key=True)
    record_date: str = Field(index=True, unique=True)  # YYYY-MM-DD
    weight_kg: float | None = None
    bowel_movement: str = Field(default="unknown")
    period_status: str | None = None
    period_day: int | None = None
    period_days_until: int | None = None
    total_kcal_min: float | None = None
    total_kcal_max: float | None = None
    total_kcal_confirmed: float | None = None
    protein_g: float | None = None
    steps: int | None = None
    water_ml: int | None = None
    analysis: str | None = None
    notes: str | None = None
    data_status: str = Field(default="estimated")
    raw_input: str | None = None
    source: str = Field(default="manual_or_ai")
    is_locked: int = Field(default=0)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


class FoodEntry(SQLModel, table=True):
    __tablename__ = "food_entries"
    id: int | None = Field(default=None, primary_key=True)
    daily_record_id: int = Field(foreign_key="daily_records.id")
    meal_type: str  # breakfast/lunch/dinner/snack/drink
    food_name: str
    quantity_text: str | None = None
    quantity_g: float | None = None
    kcal: float | None = None
    kcal_min: float | None = None
    kcal_max: float | None = None
    kcal_source: str = Field(default="estimated")
    source_note: str | None = None
    sort_order: int = Field(default=0)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


class WeightMeasurement(SQLModel, table=True):
    __tablename__ = "weight_measurements"
    id: int | None = Field(default=None, primary_key=True)
    measured_at: str  # ISO datetime
    weight_kg: float
    condition: str = Field(default="morning_fasted_after_urination")
    daily_record_id: int | None = Field(default=None, foreign_key="daily_records.id")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"
    id: int | None = Field(default=None, primary_key=True)
    entity_type: str
    entity_id: int | None = None
    action: str
    before_json: str | None = None
    after_json: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


class FoodLibraryItem(SQLModel, table=True):
    __tablename__ = "food_library"
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)  # 食物名称
    category: str = Field(default="other")  # staple/meat/veg/fruit/snack/drink/dairy/other
    calories_per_100g: float | None = None
    protein_per_100g: float | None = None
    carbs_per_100g: float | None = None
    fat_per_100g: float | None = None
    common_portion: str | None = None  # e.g. "1碗(200g)"
    common_portion_g: float | None = None
    common_portion_kcal: float | None = None
    is_custom: int = Field(default=0)  # 0=system, 1=user-added
    user_id: int | None = Field(default=None)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
