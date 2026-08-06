"""Food library search / CRUD router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select, func

from app.db import get_session
from app.models import FoodLibraryItem
from app.schemas import FoodLibraryCreate, FoodLibraryResponse, FoodSearchResult
from app.services.food_seeder import seed_food_library

router = APIRouter(prefix="/api/foods", tags=["foods"])


@router.get("/search", response_model=FoodSearchResult)
def search_foods(
    q: str = Query("", description="搜索关键词"),
    category: str | None = Query(None, description="分类筛选"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    """Search food library by name with optional category filter."""
    # Ensure seed data
    seed_food_library(session)

    conditions = []
    if q.strip():
        conditions.append(FoodLibraryItem.name.contains(q.strip()))
    if category:
        conditions.append(FoodLibraryItem.category == category)

    stmt = select(FoodLibraryItem).where(*conditions) if conditions else select(FoodLibraryItem)
    count_stmt = select(func.count()).select_from(FoodLibraryItem).where(*conditions) if conditions else select(func.count()).select_from(FoodLibraryItem)

    total = session.exec(count_stmt).one()
    items = session.exec(stmt.order_by(FoodLibraryItem.category, FoodLibraryItem.name).offset(offset).limit(limit)).all()

    return FoodSearchResult(
        items=[FoodLibraryResponse.model_validate(i) for i in items],
        total=total,
    )


@router.get("/categories")
def list_categories(session: Session = Depends(get_session)):
    """List distinct food categories with counts."""
    seed_food_library(session)
    rows = session.exec(
        select(FoodLibraryItem.category, func.count(FoodLibraryItem.id))
        .group_by(FoodLibraryItem.category)
        .order_by(FoodLibraryItem.category)
    ).all()
    return [{"category": r[0], "count": r[1]} for r in rows]


@router.post("/", response_model=FoodLibraryResponse)
def add_food(item: FoodLibraryCreate, session: Session = Depends(get_session)):
    """Add a custom food item to the library."""
    existing = session.exec(
        select(FoodLibraryItem).where(FoodLibraryItem.name == item.name.strip())
    ).first()
    if existing:
        return FoodLibraryResponse.model_validate(existing)

    new_item = FoodLibraryItem(
        name=item.name.strip(),
        category=item.category,
        calories_per_100g=item.calories_per_100g,
        protein_per_100g=item.protein_per_100g,
        carbs_per_100g=item.carbs_per_100g,
        fat_per_100g=item.fat_per_100g,
        common_portion=item.common_portion,
        common_portion_g=item.common_portion_g,
        common_portion_kcal=item.common_portion_kcal,
        is_custom=1,
    )
    session.add(new_item)
    session.commit()
    session.refresh(new_item)
    return FoodLibraryResponse.model_validate(new_item)


@router.get("/{food_id}", response_model=FoodLibraryResponse)
def get_food(food_id: int, session: Session = Depends(get_session)):
    """Get a single food item by ID."""
    item = session.get(FoodLibraryItem, food_id)
    if not item:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="食物不存在")
    return FoodLibraryResponse.model_validate(item)


@router.get("/")
def list_seed_trigger(session: Session = Depends(get_session)):
    """Trigger food library seed (useful for first-time setup)."""
    return {"seeded": seed_food_library(session)}
