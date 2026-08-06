"""AI analysis endpoint."""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import DailyRecord, UserProfile
from app.schemas import ParsePreview
from app.serialize import record_to_dict
from app.services import ai_provider

router = APIRouter(prefix="/api/ai", tags=["ai"])


def _serialize_recent(records: List[DailyRecord], session: Session) -> List[Dict[str, Any]]:
    out = []
    for r in records:
        d = record_to_dict(r, session)
        out.append({
            "record_date": d["record_date"],
            "weight_kg": d["weight_kg"],
            "bowel_movement": d["bowel_movement"],
            "period_status": d["period_status"],
            "total_kcal_min": d["total_kcal_min"],
            "total_kcal_max": d["total_kcal_max"],
            "analysis": d["analysis"],
            "food_entries": [
                {"meal_type": f["meal_type"], "food_name": f["food_name"], "quantity_text": f["quantity_text"]}
                for f in d["food_entries"]
            ],
        })
    return out


@router.post("/analyze")
async def analyze(payload: dict, session: Session = Depends(get_session)):
    text = (payload.get("text") or "").strip()
    record_date = payload.get("record_date")
    images = payload.get("images") or []
    if not record_date:
        raise HTTPException(status_code=422, detail="record_date required")
    if not text and not images:
        raise HTTPException(status_code=422, detail="text or images required")

    from app.db import ensure_user_profile
    ensure_user_profile(session)
    profile = session.get(UserProfile, 1)
    profile_dict = profile.model_dump()
    # Never leak raw key to downstream context or logs.
    profile_dict.pop("llm_api_key", None)

    # Recent 7 records excluding target date, newest first.
    recent = session.exec(
        select(DailyRecord)
        .where(DailyRecord.record_date != record_date)
        .order_by(DailyRecord.record_date.desc())
        .limit(7)
    ).all()
    recent.reverse()  # chronological order

    # Auto-select: images present → try vision model, fallback to text model.
    has_images = bool(images)
    if has_images and profile.vision_api_key:
        provider = ai_provider.get_provider(
            "zhipu",  # vision provider always OpenAI-compatible
            api_key=profile.vision_api_key,
            base_url=profile.vision_base_url or "https://open.bigmodel.cn/api/paas/v4/",
            model=profile.vision_model or "glm-4v-flash",
        )
    else:
        provider_name = payload.get("provider") or profile.llm_provider or "local"
        base_url = payload.get("base_url") or profile.llm_base_url
        api_key = payload.get("api_key") or profile.llm_api_key
        model = payload.get("model") or profile.llm_model
        provider = ai_provider.get_provider(provider_name, api_key=api_key, base_url=base_url, model=model)
    try:
        result = await provider.analyze(
            text=text,
            record_date=record_date,
            images=images,
            recent_records=_serialize_recent(recent, session),
            profile=profile_dict,
        )
    except Exception as e:
        # Surface enough detail for frontend debugging without leaking key.
        raise HTTPException(status_code=502, detail=f"AI 调用失败: {e}")

    return result


@router.post("/parse")
def parse(payload: dict, session: Session = Depends(get_session)) -> ParsePreview:
    """Keep local rule-based parse available."""
    provider = ai_provider.get_provider("local")
    return provider.parse(payload.get("text", ""), payload.get("base_date"))


@router.post("/chat")
async def chat(payload: dict, session: Session = Depends(get_session)):
    """Free-form AI nutrition Q&A."""
    message = (payload.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=422, detail="message required")
    chat_history = payload.get("history") or []

    from app.db import ensure_user_profile
    ensure_user_profile(session)
    profile = session.get(UserProfile, 1)
    profile_dict = profile.model_dump()
    profile_dict.pop("llm_api_key", None)

    recent = session.exec(
        select(DailyRecord)
        .order_by(DailyRecord.record_date.desc())
        .limit(10)
    ).all()

    provider_name = profile.llm_provider or "local"
    provider = ai_provider.get_provider(
        provider_name,
        api_key=profile.llm_api_key,
        base_url=profile.llm_base_url,
        model=profile.llm_model,
    )
    try:
        reply = await provider.chat(
            message=message,
            chat_history=chat_history,
            recent_records=_serialize_recent(recent, session),
            profile=profile_dict,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI 调用失败: {e}")

    return {"reply": reply}


@router.post("/vision-food")
async def vision_food(payload: dict, session: Session = Depends(get_session)):
    """Analyze a food photo using vision AI. Returns recognized food items."""
    image_base64 = (payload.get("image") or "").strip()
    if not image_base64:
        raise HTTPException(status_code=422, detail="image (base64) required")

    from app.db import ensure_user_profile
    ensure_user_profile(session)
    profile = session.get(UserProfile, 1)

    # Use vision provider from profile
    if not profile.vision_api_key:
        return {
            "foods": [],
            "total_kcal_estimate": 0,
            "raw_response": "未配置图像识别模型。请在设置 → AI模型配置中，填写「图片识别」的 API Key（推荐智谱 GLM-4V-Flash）。",
        }

    provider = ai_provider.get_provider(
        "zhipu",
        api_key=profile.vision_api_key,
        base_url=profile.vision_base_url or "https://open.bigmodel.cn/api/paas/v4/",
        model=profile.vision_model or "glm-4v-flash",
    )
    try:
        result = await provider.vision_food(image_base64)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"图像识别失败: {e}")
    return result
