"""Local rule-based natural-language parser (V1 placeholder).

Extracts date / weight / bowel / period and segments meals by keyword.
The result is ONLY a preview and must be confirmed by the user before saving.
No external AI API is called.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from app.schemas import ParsePreview


def _resolve_date(text: str, base: Optional[date] = None) -> str:
    today = base or date.today()
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    if re.search(r"今天|今日", text):
        return today.isoformat()
    if re.search(r"昨天|昨日", text):
        return (today - timedelta(days=1)).isoformat()
    if re.search(r"前天", text):
        return (today - timedelta(days=2)).isoformat()
    m = re.search(r"(\d{1,2})月(\d{1,2})[日号]?", text)
    if m:
        return f"{today.year:04d}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    m = re.search(r"(\d{1,2})/(\d{1,2})", text)
    if m:
        return f"{today.year:04d}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    return today.isoformat()


def _extract_weight(text: str) -> Optional[float]:
    m = re.search(r"(?:体重|晨重|称重|称|重)[^\d]{0,4}(\d{2,3}(?:\.\d+)?)", text)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d{2,3}(?:\.\d+)?)\s*(?:kg|公斤|千克)", text)
    if m:
        return float(m.group(1))
    return None


def _extract_bowel(text: str) -> Optional[str]:
    if re.search(r"没(拉|排便|上)|未(拉|排便)|没拉粑粑|没上", text):
        return "no"
    if re.search(r"前(一)?天.{0,6}(拉|排便)|前一天拉", text):
        return "previous_day_yes"
    if re.search(r"拉了粑粑|排便|上了|上厕所|拉了", text):
        return "yes"
    return None


def _extract_period(text: str) -> Tuple[Optional[str], Optional[int], Optional[int]]:
    m = re.search(r"月经第\s*(\d+)\s*天", text)
    if m:
        d = int(m.group(1))
        return (f"period_day_{d}", d, None)
    m = re.search(r"还有\s*(\d+)\s*天.*(?:来|例假|月经)", text)
    if m:
        d = int(m.group(1))
        return (f"pre_period_{d}_days", None, d)
    if re.search(r"来例假|月经来了|生理期到了|大姨妈来了|来大姨妈", text):
        return ("period", None, None)
    if re.search(r"结束后|生理期结束|例假结束", text):
        return ("period_ended", None, None)
    return (None, None, None)


def _is_drink(text: str) -> bool:
    return bool(re.search(r"咖啡|美式|拿铁|卡布|茶|可乐|雪碧|饮料|果汁|牛奶|酸奶饮|酒|奶茶|喝水|喝了|喝的|气泡水|矿泉水", text))


def _segment_meals(text: str) -> Dict[str, List[str]]:
    # canonical meal types matching the frontend editable list
    meals: Dict[str, List[str]] = {"breakfast": [], "lunch": [], "dinner": [], "snack": [], "drink": []}
    marker_re = re.compile(r"(早餐|早饭|早晨|上午|午餐|午饭|中午|晚餐|晚饭|晚上|加餐|零食|夜宵|饮料|喝的|下午)")
    matches = list(marker_re.finditer(text))
    if not matches:
        # No meal marker at all: keep the whole text as a single snack/drink note.
        seg = text.strip()
        if seg:
            (meals["drink"] if _is_drink(seg) else meals["snack"]).append(seg)
        return {k: v for k, v in meals.items() if v}
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        segment = text[start:end].strip(" ；;，,。、")
        if not segment:
            continue
        label = m.group(1)
        if label in ("早餐", "早饭", "早晨", "上午"):
            meals["breakfast"].append(segment)
        elif label in ("午餐", "午饭", "中午"):
            meals["lunch"].append(segment)
        elif label in ("晚餐", "晚饭", "晚上"):
            meals["dinner"].append(segment)
        else:
            # 加餐/零食/夜宵/饮料/喝的/下午 -> classify each segment
            (meals["drink"] if _is_drink(segment) else meals["snack"]).append(segment)
    return {k: v for k, v in meals.items() if v}


def parse_text(text: str, base: Optional[date] = None) -> ParsePreview:
    record_date = _resolve_date(text, base)
    weight = _extract_weight(text)
    bowel = _extract_bowel(text)
    status, pd, pu = _extract_period(text)
    meals = _segment_meals(text)
    return ParsePreview(
        record_date=record_date,
        weight_kg=weight,
        bowel_movement=bowel,
        period_status=status,
        period_day=pd,
        period_days_until=pu,
        meals=meals,
        raw_text=text,
        note="本地规则解析（V1占位），结果仅供参考，请确认后再保存。",
    )
