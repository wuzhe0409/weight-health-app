# 数据字典

## 核心原则

1. 历史记录只追加，不覆盖。
2. 所有历史记录保留 `raw_input`、`notes` 和 `data_status`。
3. 官方热量与用户明确提供的热量优先级最高。
4. 估算值必须保存为区间，不得伪装成精确值。
5. 修改已存在的历史记录时，必须写入 `audit_log`。
6. 用户未明确说“可食重量”时：
   - 当前约定：水果只写重量且无备注，按可食重量计算。
   - 明确写“带皮/带梗/带核”时，再按可食率折算。

## daily_records 关键字段

- `record_date`: YYYY-MM-DD，唯一。
- `weight_kg`: 晨起空腹、排尿后称重。
- `bowel_movement`: yes / no / previous_day_yes / previous_day_no / no_then_evening_yes / unknown。
- `period_status`: pre_period / period / post_period / unknown，历史数据可保留更细字符串。
- `period_day`: 月经第几天。
- `period_days_until`: 距离月经还有几天。
- `total_kcal_min`, `total_kcal_max`: 估算区间。
- `total_kcal_confirmed`: 只有证据充分时填写。
- `data_status`: confirmed / mostly_confirmed / estimated / partially_confirmed / incomplete。
- `is_locked`: 历史导入完成后设为1，前端默认禁止直接覆盖。

## food_entries 关键字段

- `meal_type`: breakfast / lunch / dinner / snack / drink。
- `kcal_source`: official / package_label / user_confirmed / estimated。
- `quantity_text`: 保留“3/4份、半碗、一个大桃子”等原始表达。
- `source_note`: 记录官方图、包装营养表、用户补充等来源。
