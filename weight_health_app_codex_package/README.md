# Weight Health App 开发包

把整个文件夹交给 Codex，并让它先阅读 `CODEX_MASTER_PROMPT.md`。

## 文件说明

- `PRD.md`：完整产品需求。
- `CODEX_MASTER_PROMPT.md`：直接发送给Codex的主提示词。
- `historical_records.csv`：历史数据，适合人工查看和导入。
- `historical_records.json`：历史数据，适合程序导入。
- `historical_records.xlsx`：Excel版历史记录和规则。
- `schema.sql`：SQLite数据库结构。
- `data_dictionary.md`：字段含义和数据保护规则。

## 重要说明

历史数据来自聊天记录整理，部分热量是估算值。所有不确定数据均通过：

- `estimated_kcal_min`
- `estimated_kcal_max`
- `data_status`
- `notes`

保留不确定性。不得把估算值改成精确值。

## 推荐给Codex的第一句话

“请打开并完整阅读这个开发包，先执行 `CODEX_MASTER_PROMPT.md`，不要修改任何历史数据。先给我输出项目目录、实施计划和数据库导入设计，等我确认后再开始编码。”
