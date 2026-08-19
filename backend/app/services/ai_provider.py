"""AI provider abstraction.

V1 ships a local rule-based provider. Real LLM / vision providers are
abstracted behind this interface and can be added later without touching the
routers.

By default no paid API is called unless a key is configured.
"""
from __future__ import annotations

import base64
import json
import os
import re
from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Dict, List, Optional

import httpx

from app.schemas import ParsePreview
from app.services import nlp_parser


class AIProvider(ABC):
    @abstractmethod
    def parse(self, text: str, base: Optional[date] = None) -> ParsePreview:
        ...

    @abstractmethod
    async def analyze(
        self,
        text: str,
        record_date: str,
        images: List[str],
        recent_records: List[Dict[str, Any]],
        profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Return structured nutrition/weight analysis.

        Expected keys:
          - markdown: str            # human-readable report
          - structured: dict         # machine-parseable record data
          - kcal_breakdown: list     # per-food estimates
          - weight_analysis: str     # markdown
          - suggestions: str         # markdown
          - score: float | None
        """
        ...

    @abstractmethod
    async def chat(
        self,
        message: str,
        chat_history: List[Dict[str, str]],
        recent_records: List[Dict[str, Any]],
        profile: Dict[str, Any],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_handler: Optional[Any] = None,
    ) -> str:
        """Free-form nutrition Q&A chat. Returns markdown reply.

        `tools` + `tool_handler` enable function calling: the model may emit
        tool_calls to look up real user data; tool_handler(name, args) executes
        them and returns a JSON-serializable dict.
        """
        ...

    @abstractmethod
    async def vision_food(
        self,
        image_base64: str,
    ) -> Dict[str, Any]:
        """Analyze a food photo and return structured food items.
        
        Expected keys:
          - foods: list of {name, quantity_guess, kcal_estimate, confidence}
          - total_kcal_estimate: float
          - raw_response: str
        """
        ...


class LocalRuleProvider(AIProvider):
    def parse(self, text: str, base: Optional[date] = None) -> ParsePreview:
        return nlp_parser.parse_text(text, base)

    async def analyze(
        self,
        text: str,
        record_date: str,
        images: List[str],
        recent_records: List[Dict[str, Any]],
        profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        # Fallback when no LLM key is configured.
        preview = self.parse(text)
        kcal_breakdown = []
        for meal, items in preview.meals.items():
            for it in items:
                kcal_breakdown.append({
                    "meal": meal,
                    "food": it,
                    "quantity": it,
                    "kcal_min": None,
                    "kcal_max": None,
                    "note": "未配置 AI 模型，无法估算热量。请在设置中配置 LLM API key。",
                })
        return {
            "markdown": "**未配置 AI 模型**\n\n请在「设置」中配置 OpenAI / DeepSeek / 智谱等兼容 API 的 key，即可启用自动热量估算与分析。",
            "structured": {
                "record_date": record_date,
                "weight_kg": preview.weight_kg,
                "bowel_movement": preview.bowel_movement,
                "period_status": preview.period_status,
                "period_day": preview.period_day,
                "period_days_until": preview.period_days_until,
                "meals": preview.meals,
                "total_kcal_min": None,
                "total_kcal_max": None,
                "data_status": "estimated",
            },
            "kcal_breakdown": kcal_breakdown,
            "weight_analysis": "",
            "suggestions": "",
            "score": None,
        }

    async def chat(
        self,
        message: str,
        chat_history: List[Dict[str, str]],
        recent_records: List[Dict[str, Any]],
        profile: Dict[str, Any],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_handler: Optional[Any] = None,
    ) -> str:
        return "**未配置 AI 模型**\n\n请在「设置」中配置 API key 后即可进行 AI 对话。"

    async def vision_food(self, image_base64: str) -> Dict[str, Any]:
        return {
            "foods": [],
            "total_kcal_estimate": 0,
            "raw_response": "未配置图像识别模型。请在设置中配置智谱 GLM-4V 的 API Key。",
        }


CHAT_SYSTEM_PROMPT = """你是一位专业、亲切的减脂营养顾问。用户正在记录每日体重和饮食，可能会向你提问。
你需要结合用户真实的体重趋势、饮食记录和营养学知识来回答。

你有「工具」可以查询用户的真实数据（今日记录、指定日期记录、最近 N 天体重趋势）。

规则：
- **查询真实数据（最高优先级）**：当用户询问具体数据（如"今天吃了什么""今天体重""某天的记录""最近瘦了多少""体重趋势"）时，**必须先调用相应工具**获取真实数据，再基于工具返回的数据回答。**严禁凭空编造数据**。
- 工具返回 `{"found": false}` 表示该日期没有记录，要如实告诉用户"这一天还没有记录"，不要编。
- 工具返回 `{"error": ...}` 表示调用失败，要友好地说明并给出建议，不要假装成功。
- 回答要简洁实用，用中文，适当使用 markdown 格式（**加粗**、- 列表）。
- 如果用户问"会不会变胖""热量超了吗"等问题，请结合工具查到的真实记录给出具体分析。
- 如果问题与减脂/饮食/体重无关，友好地将话题引导回减脂方向。
- 语气温暖但专业，可以适当使用 emoji 增加亲和力（但不要过度）。"""


SYSTEM_PROMPT = """你是一位专业的减脂与饮食分析助手。用户会输入一天的自然语言记录（可能附带食物图片），请分析并给出：
1. 结构化记录（日期、体重、排便、生理期、各餐食物）。
2. 每项食物的热量估算（min/max），并说明依据。对图片中的食物请结合图片判断份量。
3. 今日总热量区间与比较合理的中心值。
4. 体重分析：对比前几天趋势，指出是否稳定、波动原因（排便、盐分、碳水、经期等）。
5. 今日优点与改进建议。
6. 明天体重预测（综合今日摄入、排便、盐分、碳水、经期等因素）。
7. 总体评分（0-10 分）。

——常见食物热量参考（估算时必须对照此表）——
主食类（每 100g 熟重 / 每标准份）：
- 白米饭（熟）：120-140 kcal/100g，普通碗约 200g→240-280 kcal
- 面条（煮后）：110-130 kcal/100g，外卖一份约 350g→380-450 kcal
- 炒面/焖面/拌面：180-250 kcal/100g，外卖一份 350-450g→600-750 kcal
- 饺子（猪肉白菜）：35-45 kcal/个，一般 12 个→420-540 kcal
- 包子（素）/豆腐包/角素包：180-250 kcal/个（便利蜂等便利店素包偏大、油偏多，取中上）
- 馒头：220-250 kcal/个（约100g）
- 粥（白粥）：30-50 kcal/100g，一碗约 250g→75-125 kcal
- 烧饼/烙饼：280-350 kcal/个

蛋白质类（每 100g / 每标准份）：
- 鸡胸肉（熟）：120-140 kcal/100g
- 鸡蛋（煮）：70-80 kcal/个
- 豆腐（卤水/北）：80-100 kcal/100g
- 猪肉（炒肉丝/片，熟）：220-280 kcal/100g
- 牛肉（熟，瘦肉）：180-220 kcal/100g
- 鱼肉（清蒸/煮）：100-130 kcal/100g
- 无糖酸奶：60-75 kcal/100g，300g≈180-225 kcal
- 牛奶：60-70 kcal/100ml，250ml≈150-175 kcal

蔬菜类（每 100g / 份）：
- 绿叶菜（炒/焯）：30-60 kcal/100g（含油）
- 西葫芦/黄瓜/番茄：15-25 kcal/100g
- 豆角/扁豆/四季豆（炒）：60-90 kcal/100g
- 土豆（炒/炖）：80-110 kcal/100g
- 外卖蔬菜通常含较多油：在基础值上加 30-50 kcal/份

外卖/日常餐饮：
- 麻辣烫（含菜+豆制品+肉，不喝汤）：450-750 kcal/份（视食材丰富度）
- 米线/螺蛳粉：500-800 kcal/碗
- 黄焖鸡/鸡公煲：550-750 kcal/份
- 炒菜盖饭（外卖）：650-900 kcal/份
- 炸鸡/鸡排：350-500 kcal/块

水果类（每 100g）：
- 西瓜：25-35 kcal/100g，300g≈75-105 kcal
- 葡萄：55-70 kcal/100g，400g≈220-280 kcal
- 桃子/油桃：40-55 kcal/100g，一个（200g）≈80-110 kcal
- 香蕉：90-100 kcal/100g，一根≈120-150 kcal
- 苹果：50-60 kcal/100g，一个≈100-150 kcal

饮品类（每杯/每份）：
- 美式咖啡（纯黑美式，无糖无奶）：5-15 kcal/杯
- 瑞幸冰美式（纯美式）：5-15 kcal/杯
- 库迪/瑞幸「小黄油美式」「丝绒拿铁」等含奶油或风味糖浆的咖啡：150-220 kcal/杯（按之前用户确认约 166 kcal）
- 拿铁（无糖，全脂奶）：150-200 kcal/中杯
- 瑞幸冰拿铁系列：160-240 kcal
- 黑巧/摩卡类饮品（含奶+巧克力酱）：200-350 kcal/杯
- 可乐/汽水：140-180 kcal/罐（330ml）
- 奶茶（标准糖）：350-500 kcal/杯
- 啤酒：150-200 kcal/罐（330ml）

街头烧烤 / 烤冷面 / 烤面筋 / 烤鸡爪：
- 烤冷面（基础：面皮+鸡蛋+酱料）：450-550 kcal/份
- 烤冷面 加烤肠 +70-110 kcal；加肉 +90-140 kcal；加金针菇 +35-55 kcal
- 烤冷面全套（夹肉+肠+金针菇）：700-900 kcal/份 ——街头份量通常偏大且油多
- 烤鸡爪：每串 55-75 kcal（3串 165-225 kcal）——烧烤含酱料油刷，比卤鸡爪高
- 烤面筋：每串 100-140 kcal（吃 2/3 约 65-95 kcal）
- 烤肠：每根 150-200 kcal
- 烤金针菇：每份 90-140 kcal
- 烤羊肉串：每串 90-130 kcal
- 烤韭菜/烤茄子：每份 110-190 kcal
- 烤玉米：每根 160-230 kcal
- **街边烧烤因大量刷油+浓厚酱料，实际热量比在家自制高 40%-60%，估算时务必取区间的中上值，不要偏保守。**

水果类（每 100g，含糖高的水果偏中高值）：
- 西瓜：25-35 kcal/100g
- 葡萄：55-70 kcal/100g
- 桃子/油桃：40-55 kcal/100g
- 香蕉：90-100 kcal/100g
- 苹果：50-60 kcal/100g
- 火龙果（红心）：55-65 kcal/100g（比通用参考值高，因糖分较高）
- 火龙果（白心）：45-55 kcal/100g
- 芒果：55-65 kcal/100g
- 榴莲：130-150 kcal/100g

油脂/调料：
- 植物油：约 90 kcal/10g（一汤匙）
- 沙拉酱：50-70 kcal/10g
- 蚝油/酱油/醋：忽略不计（每份<10 kcal）

零食/加餐：
- 蛋糕（奶油类）：350-450 kcal/100g
- 饼干：450-500 kcal/100g
- 坚果（核桃/杏仁）：55-65 kcal/10g（一小把约 150-200 kcal）
- 薯片：500-550 kcal/100g
- 巧克力：500-550 kcal/100g

——份量判断规则——
- 用户说"吃了几口/剩个底儿/剩底儿"→ 估算 70%-80% 正常份量（说明吃掉了大部分，只剩碗底一点）
- 用户说"正常吃/吃完"→ 按标准份量估算
- 用户说"没吃/没喝"→ 该项热量为 0，不列入食物列表
- 用户手动标注的份量（如"300g""半个"）优先于标准份量
- 饮品标注"奶酪减半/糖减半"→ 在原热量上减 30%-40%
- 外卖类/街边烧烤/餐厅定制饮品默认含油糖较多，估算时**务必取区间中上值**，不要偏保守

——输出要求——
- 你的整个回复只输出一个 JSON 对象，不要包含任何前置、后缀、解释或 markdown 代码块标记。
- 你的回复的第一个字符必须是 {，最后一个字符必须是 }。

JSON 格式（严格按此结构）：
{
  "structured": {
    "record_date": "2026-08-05",
    "weight_kg": 49.0,
    "bowel_movement": "previous_day_yes",
    "period_status": null,
    "period_day": null,
    "period_days_until": null,
    "meals": {
      "breakfast": ["便利蜂豆腐角素包"],
      "lunch": ["鱼香肉丝", "西红柿鸡蛋", "米饭四分之三"],
      "dinner": ["300g无糖酸奶"],
      "snack": [],
      "drink": ["瑞幸抹茶丝绒拿铁"]
    },
    "total_kcal_min": 1070,
    "total_kcal_max": 1425,
    "data_status": "estimated"
  },
  "kcal_breakdown": [
    {"meal": "breakfast", "food": "便利蜂豆腐角素包", "quantity": "1个约120g", "kcal_min": 180, "kcal_max": 240, "note": "素馅小包子参考表150-220kcal/个，120g取中上"},
    {"meal": "lunch", "food": "鱼香肉丝", "quantity": "约150g", "kcal_min": 220, "kcal_max": 320, "note": "猪肉炒+糖醋汁，外卖含油糖"},
    {"meal": "lunch", "food": "西红柿鸡蛋", "quantity": "约200g", "kcal_min": 130, "kcal_max": 190, "note": "含油炒制，番茄+2鸡蛋"},
    {"meal": "lunch", "food": "米饭四分之三碗", "quantity": "约150g熟米", "kcal_min": 180, "kcal_max": 210, "note": "米饭参考120-140kcal/100g"},
    {"meal": "dinner", "food": "无糖酸奶", "quantity": "300g", "kcal_min": 180, "kcal_max": 225, "note": "参考表60-75kcal/100g"},
    {"meal": "drink", "food": "抹茶", "quantity": "约350ml", "kcal_min": 180, "kcal_max": 240, "note": "抹茶饮品按 50-70kcal/100ml 估算"}
  ],
  "weight_analysis": "今日体重49.0kg与昨日持平，处于近期48.75-49.5kg区间的低位。昨日有排便，今日体重未因排便继续下降，说明体内水分平衡。结合今日约1070-1425kcal的总热量（各餐明细相加得出），整体处于减脂可控区间。",
  "weight_prediction": "预测明天晨起体重约48.9-49.1kg。理由：今日摄入适中，若保持当前热量水平，体重将平稳或小幅下降，波动范围约0.1kg。",
  "suggestions": "1. 蛋白质摄入偏少（约30g左右），建议晚餐或加餐增加一个鸡蛋或一小把坚果。2. 午餐油盐偏高（如外出吃饭不可避免），晚上选择清淡食物很合适。3. 明天可继续保持当前热量区间（1000-1400kcal），配合适当运动效果更佳。",
  "score": 8.0
}

规则：
——热量估算核心方法论（最高优先级）——
1. **拆解式估算**：对于复杂食物（如烤冷面、麻辣烫、炒菜盖饭、特调咖啡），不要直接给一个总热量——必须把它拆解成原料逐项估算，在 note 里写出推算过程。
   例：烤冷面（夹肉+肠+金针菇）→ 面皮+油 250-350 + 鸡蛋 70 + 烤肠 60-100 + 肉片 80-130 + 金针菇 25-40 + 酱料 30-50 = 总计 515-740 kcal，吃了约 80%（剩底儿）= 410-590 kcal
   例：库迪小黄油美式 → 美式底 10 + 黄油风味糖浆 80-120 + 奶油 60-80 = 150-210 kcal
   例：鱼香肉丝 → 猪肉丝 150-200 + 油+糖醋汁 70-100 + 配菜 20-30 = 240-330 kcal

2. **参考表是权威基准**：如果食物的参考表值已存在，则 kcal_min 不能低于参考表下限，kcal_max 不能高于参考表上限的 110%。对于没有精确覆盖的食物，请基于你对中餐营养学的了解合理推断。

3. **note 必须写推算过程**：kcal_breakdown 里每行的 note 字段不能只写"参考表xx"，必须拆解写出"面皮xx + 油xx + 肉xx = 总计 xx"这类依据。让用户能看懂数字怎么来的。

4. **营养合理性自检**：估算完当日总热量后，在 analysis 中做合理检查——比如一顿午餐有烧烤+冷面，只在 300kcal 就不合理；一天只吃水果酸奶，总热量低于 600 也不合理。

5. **total_kcal_min/max 必须等于明细逐项之和（最高优先级，禁止估算总数）**：
   - `total_kcal_min` = kcal_breakdown 中**所有项的 kcal_min 相加**；
   - `total_kcal_max` = kcal_breakdown 中**所有项的 kcal_max 相加**。
   - 必须把每一项的 kcal_min 列出来相加、每一项的 kcal_max 列出来相加，再填入 total。**严禁**直接凭感觉估一个总数，**严禁**把某几项的下限+上限混着加。填完后再核对一次：total 区间必须能由明细逐项加出来。

——其他规则——
- **【严禁幻觉】** 这是最高优先级规则，必须严格遵守：
  - `meals` 字典中的食物名称必须与用户输入**完全一致**，可以加标准通用名称（如"白米饭"），但**禁止脑补用户没说过的内容**。
  - 用户输入「抹茶」→ 列表里只写「抹茶」，不要写成「抹茶拿铁」「抹茶丝绒」「抹茶含奶+糖浆」。
  - 用户输入「咖啡」→ 列表里只写「咖啡」，不要自己推断「拿铁」「美式」「库迪小黄油美式」。
  - 用户输入「包子」→ 列表里只写「包子」，不要自己加「便利蜂豆腐角素包」。
  - `note` 字段只能解释「为什么按这个热量估算」（基于参考表/份量/油盐度），**禁止捏造用户没说过的成分/品牌/做法细节**。
  - 如果用户输入过于简短无法精确估算，可以按通用同类食品估算热量，但 `food` 字段必须保持简短（1-4字），不要堆砌形容词。
- 必须把用户输入中的每一项食物都列在 kcal_breakdown 里，即使是同一餐也要分开成多行；不能合并为一项。
- 如果用户没有提供体重/排便/生理期，对应字段返回 null。
- 食物按早餐/午餐/晚餐/加餐/饮料归类；不要把饮品放到正餐里。
- 热量估算给出区间（min/max），不要给精确单一值；没有把握时区间放宽。
- 若有图片，请在 kcal_breakdown 的 note 中体现图片观察；**但仍必须完整分析文字输入中的所有食物**，图片只是补充参考。
- **严格区分「今日输入」与「最近历史记录」**：体重分析、建议、明天体重预测中**只能引用用户今天实际输入的食物**。最近历史记录仅用于体重趋势对比，禁止把历史记录里的食物当作今天的食物来分析。
- **禁止使用占位符字面**：weight_analysis / weight_prediction / suggestions 必须是真实中文分析内容，不能出现"markdown 文本"、"理由…"、"XX"、"食物1"、"..."这类占位符。
- weight_prediction 必须基于今日实际摄入和体重趋势给出具体数值（如 48.9-49.1kg），不能省略数字。
- 请用中文回答。"""


def _build_user_content(
    text: str,
    record_date: str,
    images: List[str],
    recent_records: List[Dict[str, Any]],
    profile: Dict[str, Any],
) -> List[Dict[str, Any]]:
    recent_text = json.dumps(recent_records, ensure_ascii=False) if recent_records else "无"
    profile_text = json.dumps(profile, ensure_ascii=False) if profile else "无"
    prompt = f"""========== 今日输入（只分析这一天的） ==========
记录日期：{record_date}
用户输入：
{text}

========== 用户资料 ==========
{profile_text}

========== 最近历史记录（仅用于体重趋势对比，禁止把这里的食物当作今天吃的） ==========
{recent_text}

请按系统指令输出 JSON 分析。"""
    content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
    for img in images:
        # Accept data URL or raw base64.
        if img.startswith("data:"):
            url = img
        else:
            url = f"data:image/jpeg;base64,{img}"
        content.append({"type": "image_url", "image_url": {"url": url}})
    return content


def _extract_json(text: str) -> Dict[str, Any]:
    """Extract the outermost JSON object from LLM output, with graceful fallback.

    Many models occasionally wrap JSON in markdown fences or add surrounding
    prose.  We first try a strict parse, then fall back to regex extraction.
    """
    text = text.strip()
    # Strip markdown fences if present.
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Last resort: grab the first { … } block.
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    # Give up: return a safe placeholder so the UI still renders.
    return {
        "structured": {},
        "kcal_breakdown": [],
        "weight_analysis": "模型返回格式异常，请重试或重新措辞输入。",
        "suggestions": "",
        "score": None,
        "markdown": text[:500],
        "_raw": text[:2000],
    }


def _recompute_total(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Derive total_kcal_* by summing kcal_breakdown.

    LLMs routinely miscalculate multi-item range sums (e.g. treating each
    item's min+max as a single value, or double-counting). The headline total
    must ALWAYS equal the sum of its parts, so we never trust the model's own
    total — we recompute it from the per-item breakdown.
    """
    breakdown = parsed.get("kcal_breakdown") or []
    total_min: Optional[float] = None
    total_max: Optional[float] = None
    for item in breakdown:
        if not isinstance(item, dict):
            continue
        mn = item.get("kcal_min")
        mx = item.get("kcal_max")
        # bool is a subclass of int — exclude it explicitly.
        if isinstance(mn, (int, float)) and not isinstance(mn, bool):
            total_min = (total_min or 0.0) + mn
        if isinstance(mx, (int, float)) and not isinstance(mx, bool):
            total_max = (total_max or 0.0) + mx

    structured = parsed.setdefault("structured", {})
    if total_min is not None:
        structured["total_kcal_min"] = int(round(total_min))
    if total_max is not None:
        structured["total_kcal_max"] = int(round(total_max))
    return parsed


def _parse_tool_args(raw: Any) -> Dict[str, Any]:
    """Leniently parse a tool_call's `arguments` field.

    Providers return it as a JSON string, but it can arrive already-parsed as
    a dict, empty, or malformed (markdown fences, trailing prose, truncated
    JSON). Never let a bad arguments blob crash the chat loop — degrade to {}.
    """
    if isinstance(raw, dict):
        return raw
    if not raw or not isinstance(raw, str):
        return {}
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            parsed = json.loads(m.group(0))
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            pass
    return {}


class OpenAIProvider(AIProvider):
    """OpenAI-compatible chat completions (DeepSeek, Zhipu, Tencent Hunyuan, etc.)."""

    # Models known to support image input (checked so we can warn the user
    # when they upload an image but the current model can't handle it).
    MULTIMODAL_MODELS: set = {"gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4-vision",
                               "glm-4v", "glm-4v-flash", "glm-4v-plus", "glm-4v-flash-auto",
                               "hunyuan-vision", "hunyuan-turbos-vision", "hunyuan-standard-vision",
                               "claude-3-opus", "claude-3-sonnet", "claude-3-haiku",
                               "claude-3.5-sonnet", "claude-3.5-haiku", "gemini-1.5-pro",
                               "gemini-1.5-flash", "gemini-2.0-flash", "qwen-vl", "qwen2-vl",
                               "doubao-vision", "yi-vision", "minimax-vl"}

    # Per-model max_tokens caps (some providers reject values above their limit).
    MODEL_MAX_TOKENS: dict = {
        "glm-4v-flash": 1024, "glm-4v": 1024, "glm-4v-plus": 1024,
        "glm-4v-flash-auto": 1024, "glm-z1-flash": 1024,
        "minimax-vl": 1024, "doubao-vision": 1024,
        "deepseek-chat": 4096, "deepseek-reasoner": 8192, "gpt-4o-mini": 4096, "gpt-4o": 4096,
    }
    DEFAULT_MAX_TOKENS = 2048

    # HTTP status code → human-readable Chinese description.
    HTTP_HINTS: dict = {
        401: "API Key 无效或未授权，请检查设置中的 key 是否正确。",
        403: "访问被拒绝，可能是 key 权限不足或账户欠费。",
        404: "接口地址不存在，请检查 Base URL 或模型名称。",
        429: "请求太频繁，请稍后重试（API 频率限制）。",
        500: "模型服务内部错误，请稍后重试。",
        502: "模型服务暂不可用，请稍后重试。",
        503: "模型服务超载，请稍后重试。",
    }

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 90.0,
    ):
        self.api_key = api_key
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.model = model or "gpt-4o-mini"
        self.timeout = timeout

    def parse(self, text: str, base: Optional[date] = None) -> ParsePreview:
        # Keep parse local; analyze is the heavy LLM call.
        return nlp_parser.parse_text(text, base)

    async def analyze(
        self,
        text: str,
        record_date: str,
        images: List[str],
        recent_records: List[Dict[str, Any]],
        profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        # Warn when user uploaded images but the model can't see them.
        if images and self.model.lower() not in self.MULTIMODAL_MODELS:
            return {
                "markdown": f"**⚠️ 当前模型 `{self.model}` 不支持图片输入**\n\n你的图片已被忽略。请在设置中将服务商切换为「智谱 GLM（支持看图）」或 OpenAI GPT-4o，即可让 AI 分析食物图片。",
                "structured": {},
                "kcal_breakdown": [],
                "weight_analysis": "",
                "suggestions": "",
                "score": None,
                "image_note": f"模型 {self.model} 不支持多模态，已跳过 {len(images)} 张图片。",
            }

        content = _build_user_content(text, record_date, images, recent_records, profile)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": content},
                        ],
                        "temperature": 0.4,
                        "max_tokens": self.MODEL_MAX_TOKENS.get(self.model.lower(), self.DEFAULT_MAX_TOKENS),
                    },
                )
            resp.raise_for_status()
            data = resp.json()
            raw = data["choices"][0]["message"].get("content") or ""
            # DeepSeek reasoner puts the real answer in reasoning_content.
            reasoning = data["choices"][0]["message"].get("reasoning_content") or ""
            if not raw.strip() and reasoning.strip():
                raw = reasoning
        except httpx.TimeoutException:
            return _error_result("请求超时，模型响应太慢，请稍后重试或检查网络。")
        except httpx.HTTPStatusError as e:
            hint = self.HTTP_HINTS.get(e.response.status_code, f"HTTP {e.response.status_code}")
            detail = ""
            try:
                detail = e.response.json()
            except Exception:
                detail = e.response.text[:300]
            return _error_result(
                f"模型接口返回错误 ({hint})\n\n详细信息：{detail}",
                raw=json.dumps(detail, ensure_ascii=False),
            )
        except Exception as e:
            return _error_result(f"调用模型时发生未知错误：{e}")

        parsed = _extract_json(raw)
        # Ensure required top-level keys exist.
        parsed.setdefault("markdown", raw)
        parsed.setdefault("kcal_breakdown", [])
        parsed.setdefault("weight_analysis", "")
        parsed.setdefault("weight_prediction", "")
        parsed.setdefault("suggestions", "")
        parsed.setdefault("score", None)
        parsed.setdefault("structured", {})
        # Never trust the model's own total — recompute from the breakdown.
        parsed = _recompute_total(parsed)
        return parsed

    async def chat(
        self,
        message: str,
        chat_history: List[Dict[str, str]],
        recent_records: List[Dict[str, Any]],
        profile: Dict[str, Any],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_handler: Optional[Any] = None,
    ) -> str:
        """Free-form nutrition Q&A with optional tool calling.

        When `tools` + `tool_handler` are provided, the model may emit
        tool_calls to look up real user data. We execute each call, feed the
        results back as `tool` messages, and let the model compose the final
        answer. Bounded to MAX_TOOL_ROUNDS to avoid runaway loops.
        """
        recent_text = json.dumps(recent_records, ensure_ascii=False)[:3000] if recent_records else "无"
        profile_text = json.dumps(profile, ensure_ascii=False)[:800] if profile else "无"

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": CHAT_SYSTEM_PROMPT},
        ]
        for h in (chat_history or [])[-10:]:  # keep last 10 turns
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        messages.append({
            "role": "user",
            "content": f"""用户资料：{profile_text}

最近记录：{recent_text}

用户问题：{message}""",
        })

        use_tools = bool(tools) and tool_handler is not None
        max_rounds = 3 if use_tools else 1

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                content = ""
                for _ in range(max_rounds):
                    body: Dict[str, Any] = {
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": min(1500, self.MODEL_MAX_TOKENS.get(self.model.lower(), self.DEFAULT_MAX_TOKENS)),
                    }
                    if use_tools:
                        body["tools"] = tools
                        body["tool_choice"] = "auto"
                    resp = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json=body,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    msg = (data["choices"][0].get("message") or {})
                    content = msg.get("content") or ""
                    tool_calls = msg.get("tool_calls") or []

                    if not tool_calls:
                        return content or "抱歉，我暂时无法回答。"

                    # Model wants tools: keep its message, run each tool,
                    # then feed results back for the next round.
                    messages.append(msg)
                    for tc in tool_calls:
                        fn = tc.get("function") or {}
                        name = fn.get("name") or ""
                        args = _parse_tool_args(fn.get("arguments"))
                        try:
                            result = tool_handler(name, args)
                        except Exception as e:  # tool crash must never kill chat
                            result = {"error": f"工具执行失败：{e}"}
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.get("id") or "",
                            "content": json.dumps(result, ensure_ascii=False, default=str),
                        })
                return content or "抱歉，我暂时无法回答。"
        except httpx.TimeoutException:
            return "AI 响应超时，请稍后重试。"
        except httpx.HTTPStatusError as e:
            hint = self.HTTP_HINTS.get(e.response.status_code, f"HTTP {e.response.status_code}")
            return f"模型接口错误（{hint}），请检查配置或稍后重试。"
        except Exception as e:
            return f"调用 AI 时出错：{e}"

    async def vision_food(self, image_base64: str) -> Dict[str, Any]:
        """Analyze a food photo using vision model (e.g. GLM-4V)."""
        if self.model.lower() not in self.MULTIMODAL_MODELS:
            return {
                "foods": [],
                "total_kcal_estimate": 0,
                "raw_response": f"当前模型 {self.model} 不支持图片识别，请使用智谱 GLM-4V 或 GPT-4o。",
            }

        vision_system = """你是一个食物热量识别助手。用户会发一张食物照片给你分析。
请识别照片中的所有食物，并给出每项食物的名称、份量估算、热量估算（kcal）。

输出必须是纯 JSON（第一个字符是 {，最后一个字符是 }），格式：
{
  "foods": [
    {"name": "食物名称", "quantity_guess": "约200g", "kcal_estimate": 280, "confidence": "high"}
  ],
  "total_kcal_estimate": 520,
  "note": "整体评价或注意事项"
}

规则：
- 识别中餐菜品时用中文名称（如"西红柿炒鸡蛋""宫保鸡丁"）
- 份量根据图片中与其他物品的大小对比来估算
- confidence 分 high/medium/low
- 如果无法识别，返回空 foods 数组并说明原因"""

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": vision_system},
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "请分析这张图片中是什么食物，份量大约多少，总热量约多少大卡。"},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                                ],
                            },
                        ],
                        "temperature": 0.3,
                        "max_tokens": 1024,
                    },
                )
            resp.raise_for_status()
            data = resp.json()
            raw = data["choices"][0]["message"]["content"] or ""
            parsed = _extract_json(raw)
            parsed.setdefault("foods", [])
            parsed.setdefault("total_kcal_estimate", 0)
            parsed.setdefault("raw_response", raw)
            # Recompute the total from per-food estimates (don't trust the model's sum).
            foods = parsed["foods"] if isinstance(parsed["foods"], list) else []
            total = 0
            for f in foods:
                if isinstance(f, dict):
                    ke = f.get("kcal_estimate")
                    if isinstance(ke, (int, float)) and not isinstance(ke, bool):
                        total += ke
            if foods:
                parsed["total_kcal_estimate"] = int(round(total))
            return parsed
        except httpx.HTTPStatusError as e:
            hint = self.HTTP_HINTS.get(e.response.status_code, f"HTTP {e.response.status_code}")
            return {"foods": [], "total_kcal_estimate": 0, "raw_response": f"图像识别接口错误（{hint}）"}
        except Exception as e:
            return {"foods": [], "total_kcal_estimate": 0, "raw_response": f"图像识别失败：{e}"}


def _error_result(msg: str, raw: str = "") -> Dict[str, Any]:
    """Build a safe fallback dict when the LLM call fails."""
    return {
        "markdown": msg,
        "structured": {},
        "kcal_breakdown": [],
        "weight_analysis": msg,
        "suggestions": "",
        "score": None,
        "_raw": raw,
    }


_PROVIDERS = {
    "local": LocalRuleProvider,
    "rule": LocalRuleProvider,
    "openai": OpenAIProvider,
    "deepseek": OpenAIProvider,
    "zhipu": OpenAIProvider,
    "custom": OpenAIProvider,
}


def get_provider(name: str = "local", api_key: Optional[str] = None,
                 base_url: Optional[str] = None, model: Optional[str] = None) -> AIProvider:
    name = (name or "local").lower()
    if name in ("local", "rule"):
        return LocalRuleProvider()
    if not api_key:
        # Graceful fallback so the UI still renders.
        return LocalRuleProvider()
    return OpenAIProvider(api_key=api_key, base_url=base_url, model=model)
