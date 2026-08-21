"""Unit tests for the AI-provider safety-net helpers.

These pure functions are the last line of defense when LLMs return malformed
output — they must never crash and must never trust the model's own totals.
"""
from app.services.ai_provider import _extract_json, _recompute_total, _parse_tool_args


# ── _extract_json ──────────────────────────────────────────────

class TestExtractJson:
    def test_plain_json(self):
        result = _extract_json('{"structured": {"weight_kg": 49.0}, "score": 8}')
        assert result["structured"]["weight_kg"] == 49.0
        assert result["score"] == 8

    def test_markdown_fenced_json(self):
        result = _extract_json('```json\n{"structured": {}, "score": 7}\n```')
        assert result["score"] == 7

    def test_json_with_surrounding_prose(self):
        result = _extract_json('好的，分析如下：\n{"score": 6}\n希望对你有帮助')
        assert result["score"] == 6

    def test_garbage_returns_safe_placeholder(self):
        result = _extract_json("这不是 JSON，模型彻底跑偏了")
        assert result["structured"] == {}
        assert result["kcal_breakdown"] == []
        assert result["score"] is None
        assert "格式异常" in result["weight_analysis"]
        assert "_raw" in result

    def test_empty_string_returns_placeholder(self):
        result = _extract_json("")
        assert result["structured"] == {}
        assert result["score"] is None

    def test_truncated_json_falls_back(self):
        # Starts like JSON but is truncated — regex grabs a block that fails to parse
        result = _extract_json('{"structured": {"weight_kg": 49.0, "broken')
        assert "weight_analysis" in result  # placeholder, not a crash


# ── _recompute_total ───────────────────────────────────────────

class TestRecomputeTotal:
    def test_sums_breakdown_ranges(self):
        parsed = {
            "structured": {"total_kcal_min": 999, "total_kcal_max": 999},  # model's wrong total
            "kcal_breakdown": [
                {"food": "包子", "kcal_min": 180, "kcal_max": 240},
                {"food": "米饭", "kcal_min": 180.4, "kcal_max": 210.6},
            ],
        }
        result = _recompute_total(parsed)
        # Must equal sum of parts, never the model's own total
        assert result["structured"]["total_kcal_min"] == 360
        assert result["structured"]["total_kcal_max"] == 451

    def test_missing_breakdown_leaves_structured_untouched(self):
        parsed = {"structured": {"total_kcal_min": 500, "total_kcal_max": 600}}
        result = _recompute_total(parsed)
        assert result["structured"]["total_kcal_min"] == 500

    def test_items_without_kcal_are_skipped(self):
        parsed = {
            "kcal_breakdown": [
                {"food": "苹果", "kcal_min": 100, "kcal_max": 150},
                {"food": "未知食物"},  # no kcal fields
                "not-a-dict",          # malformed item
            ],
        }
        result = _recompute_total(parsed)
        assert result["structured"]["total_kcal_min"] == 100
        assert result["structured"]["total_kcal_max"] == 150

    def test_bool_kcal_values_are_excluded(self):
        # bool is a subclass of int — must not be summed as 1/0
        parsed = {
            "kcal_breakdown": [
                {"food": "a", "kcal_min": True, "kcal_max": False},
                {"food": "b", "kcal_min": 200, "kcal_max": 250},
            ],
        }
        result = _recompute_total(parsed)
        assert result["structured"]["total_kcal_min"] == 200
        assert result["structured"]["total_kcal_max"] == 250

    def test_creates_structured_if_missing(self):
        result = _recompute_total({"kcal_breakdown": [{"kcal_min": 10, "kcal_max": 20}]})
        assert result["structured"]["total_kcal_min"] == 10
        assert result["structured"]["total_kcal_max"] == 20


# ── _parse_tool_args ───────────────────────────────────────────

class TestParseToolArgs:
    def test_dict_passthrough(self):
        assert _parse_tool_args({"date": "2026-08-21"}) == {"date": "2026-08-21"}

    def test_json_string(self):
        assert _parse_tool_args('{"days": 7}') == {"days": 7}

    def test_fenced_json_string(self):
        assert _parse_tool_args('```json\n{"days": 14}\n```') == {"days": 14}

    def test_none_and_empty(self):
        assert _parse_tool_args(None) == {}
        assert _parse_tool_args("") == {}

    def test_malformed_json_degrades_to_empty(self):
        assert _parse_tool_args("{not valid json") == {}

    def test_json_with_trailing_prose(self):
        assert _parse_tool_args('{"days": 3} 这是查询参数') == {"days": 3}

    def test_non_dict_json_degrades_to_empty(self):
        # A JSON array is valid JSON but not a valid args object
        assert _parse_tool_args('[1, 2, 3]') == {}

    def test_wrong_type_degrades_to_empty(self):
        assert _parse_tool_args(12345) == {}
