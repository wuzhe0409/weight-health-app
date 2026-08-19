"""AI analysis endpoint."""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import DailyRecord, UserProfile
from app.schemas import ParsePreview
from app.serialize import record_to_dict
from app.services import ai_provider

router = APIRouter(prefix="/api/ai", tags=["ai"])

# Fields that must NEVER be sent inside an LLM prompt (they would leak to the
# third-party model provider).
_SENSITIVE_PROFILE_FIELDS = ("llm_api_key", "vision_api_key")


def _sanitize_profile_for_prompt(profile: UserProfile) -> Dict[str, Any]:
    """Dump profile for prompt context, stripping all secret fields."""
    d = profile.model_dump()
    for k in _SENSITIVE_PROFILE_FIELDS:
        d.pop(k, None)
    return d


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


# ── Chat function-calling tools ──
# The model can call these to look up real user data instead of hallucinating.

TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "query_today_record",
            "description": "查询用户「今天」的健康记录（体重、排便、生理期、各餐食物、总热量、分析）。当用户问『今天的数据』『今天吃了什么』『今天体重多少』『今天热量多少』等需要查看今日记录的问题时，必须调用本工具获取真实数据，禁止凭空编造。",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_record_by_date",
            "description": "查询用户「指定日期」的健康记录（体重、排便、生理期、各餐食物、总热量、分析）。当用户问『X月X日』『某天吃了什么』『某天体重』等需要查看历史某天记录的问题时，调用本工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "要查询的日期，格式 YYYY-MM-DD"},
                },
                "required": ["date"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_weight_trend",
            "description": "查询用户最近 N 天的体重趋势与总热量，返回每天数据及首尾体重差。当用户问『最近瘦/胖了多少』『体重变化趋势』『最近几天体重』等需要看趋势或统计的问题时，调用本工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "统计最近多少天，默认 7，范围 1-90"},
                },
                "additionalProperties": False,
            },
        },
    },
]


def _query_record_dict(record_date: str, session: Session) -> Dict[str, Any]:
    """Return a compact, model-friendly view of one day's record."""
    rec = session.exec(
        select(DailyRecord).where(DailyRecord.record_date == record_date)
    ).first()
    if rec is None:
        return {"found": False, "date": record_date, "message": "该日期没有记录"}
    full = record_to_dict(rec, session)
    return {
        "found": True,
        "date": record_date,
        "weight_kg": full.get("weight_kg"),
        "bowel_movement": full.get("bowel_movement"),
        "period_status": full.get("period_status"),
        "period_day": full.get("period_day"),
        "total_kcal_min": full.get("total_kcal_min"),
        "total_kcal_max": full.get("total_kcal_max"),
        "food_entries": [
            {
                "meal_type": f.get("meal_type"),
                "food_name": f.get("food_name"),
                "quantity_text": f.get("quantity_text"),
            }
            for f in full.get("food_entries", [])
        ],
        "analysis": full.get("analysis"),
    }


def _query_weight_trend(days: int, session: Session) -> Dict[str, Any]:
    days = max(1, min(days, 90))
    records = session.exec(
        select(DailyRecord).order_by(DailyRecord.record_date.desc()).limit(days)
    ).all()
    records = list(reversed(records))  # chronological
    items = [
        {
            "date": r.record_date,
            "weight_kg": r.weight_kg,
            "total_kcal_min": r.total_kcal_min,
            "total_kcal_max": r.total_kcal_max,
        }
        for r in records
    ]
    weights = [r.weight_kg for r in records if r.weight_kg is not None]
    delta = None
    if len(weights) >= 2:
        delta = round(weights[-1] - weights[0], 2)
    return {"days": days, "count": len(records), "items": items, "weight_delta_kg": delta}


def _execute_tool(name: str, args: Dict[str, Any], session: Session) -> Dict[str, Any]:
    """Dispatch a tool call. Returns a JSON-serializable dict (never raises)."""
    try:
        if name == "query_today_record":
            return _query_record_dict(date.today().isoformat(), session)
        if name == "query_record_by_date":
            d = (args or {}).get("date")
            if not d or not isinstance(d, str):
                return {"error": "缺少日期参数 date（格式 YYYY-MM-DD）"}
            return _query_record_dict(d, session)
        if name == "query_weight_trend":
            raw_days = (args or {}).get("days")
            try:
                days = int(raw_days) if raw_days is not None else 7
            except (TypeError, ValueError):
                days = 7
            return _query_weight_trend(days, session)
        return {"error": f"未知工具：{name}"}
    except Exception as e:
        return {"error": f"工具执行失败：{e}"}


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
    profile_dict = _sanitize_profile_for_prompt(profile)

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
    profile_dict = _sanitize_profile_for_prompt(profile)

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
            tools=TOOLS,
            tool_handler=lambda name, args: _execute_tool(name, args, session),
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
