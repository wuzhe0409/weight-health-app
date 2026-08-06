"""User profile GET / PUT (settings page)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session, ensure_user_profile
from app.models import UserProfile

router = APIRouter(prefix="/api/profile", tags=["profile"])

PROFILE_FIELDS = ("gender", "age", "height_cm", "frame_size", "target_weight_kg", "bmr_formula",
                  "llm_provider", "llm_base_url", "llm_api_key", "llm_model",
                  "vision_api_key", "vision_base_url", "vision_model")


def _mask_key(key: str | None) -> str | None:
    if not key:
        return key
    if len(key) <= 8:
        return "*" * len(key)
    return key[:4] + "*" * (len(key) - 8) + key[-4:]


@router.get("")
def get_profile(session: Session = Depends(get_session)):
    ensure_user_profile(session)
    p = session.get(UserProfile, 1)
    d = p.model_dump()
    d["llm_api_key"] = _mask_key(d.get("llm_api_key"))
    d["vision_api_key"] = _mask_key(d.get("vision_api_key"))
    # Friendly defaults for first-time users.
    if not d.get("llm_provider"):
        d["llm_provider"] = "deepseek"
    if not d.get("llm_model"):
        d["llm_model"] = "deepseek-chat"
    if not d.get("llm_base_url"):
        d["llm_base_url"] = "https://api.deepseek.com/v1"
    if not d.get("vision_model"):
        d["vision_model"] = "glm-4v-flash"
    if not d.get("vision_base_url"):
        d["vision_base_url"] = "https://open.bigmodel.cn/api/paas/v4/"
    return d


@router.put("")
def update_profile(payload: dict, session: Session = Depends(get_session)):
    ensure_user_profile(session)
    p = session.get(UserProfile, 1)
    for k in PROFILE_FIELDS:
        if k in payload:
            setattr(p, k, payload[k])
    p.updated_at = datetime.now().isoformat(timespec="seconds")
    session.commit()
    session.refresh(p)
    return p.model_dump()
