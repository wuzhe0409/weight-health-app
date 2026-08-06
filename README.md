# 减脂健康记录 App (Weight Health App)

一个用于记录每日体重、饮食、排便、生理期并可视化趋势的 Web 应用。
技术栈：**FastAPI + SQLite**（后端）/ **Vue3 + Vite + TypeScript + Element Plus + ECharts**（前端）。

> 历史数据来自 `weight_health_app_codex_package`（PRD/数据字典见 `docs/`）。
> **原始数据文件零改动**：导入源是 `backend/seed/` 的只读拷贝（`chmod 444`），所有写入都落在项目内 SQLite。

---

## 快速开始

### 方式一：一键启动（推荐）
```bash
bash start.sh
# 或
make dev
```
启动后：
- 前端：http://localhost:5173 （Vite 会把 `/api` 代理到后端）
- 后端 API 文档：http://127.0.0.1:8011/docs

### 方式二：分别启动
```bash
# 后端
cd backend && /Users/wuzhe/.workbuddy/binaries/python/envs/default/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8011 --reload
# 前端（另开一个终端）
cd frontend && /Users/wuzhe/.workbuddy/binaries/node/versions/22.22.2/bin/npm run dev -- --port 5173
```

### 首次依赖安装
```bash
make install
```

---

## 功能

- **今日记录**：自然语言录入（如「6月18日 体重49.5 没拉粑粑 月经第3天 早餐吃了包子」）→ 本地规则解析预览 → 可编辑食物清单 → 保存（含「更正模式」生成 revision）。
- **历史日历**：月历视图 + 关键词搜索，点击任意日期查看详情。
- **趋势**：每日体重折线 + **7 日滚动平均**、每日热量区间图、排便标记、生理期阴影、最低/最高/最近稳定体重。
- **单日详情**：体重、餐食清单、热量区间、分析、原始录入文本。
- **设置**：个人资料 / 热量目标 / 数据导入导出（JSON / CSV）。

---

## 历史数据导入（幂等、锁定、审计）

- 导入源：`backend/seed/historical_records.json`（23 条，**权威源**；xlsx 仅参考，缺失 4 天不参与导入）。
- 导入后每条记录 `is_locked = 1`，不可直接覆盖；修改走 revision。
- 幂等：重复导入已存在的日期会被 `skipped`，绝不重复或覆盖。

```bash
make import          # 实际导入
make test            # 跑导入/幂等测试
# 或在后端目录：dry-run 只校验不写库
curl -X POST "http://127.0.0.1:8011/api/import/history?dry_run=true"
```

---

## 数据库验证

```bash
# 查看记录数与锁定情况
cd backend
/Users/wuzhe/.workbuddy/binaries/python/envs/default/bin/python - <<'PY'
import sqlite3
c = sqlite3.connect('data/app.db')
print("daily_records:", c.execute("select count(*) from daily_records").fetchone()[0])
print("locked:", c.execute("select count(*) from daily_records where is_locked=1").fetchone()[0])
print("food_entries:", c.execute("select count(*) from food_entries").fetchone()[0])
print("audit_log batches:", c.execute("select count(*) from audit_log").fetchone()[0])
PY
```

---

## 目录结构

```
mywebsite2/
├── Makefile / start.sh        # 一键启动
├── backend/                   # FastAPI + SQLite
│   ├── app/                   # main / db / models / schemas / routers / services / serialize
│   ├── seed/                  # 只读历史数据拷贝（chmod 444）
│   ├── data/                  # app.db（gitignore）
│   └── tests/test_import.py
├── frontend/                  # Vue3 + Vite + TS + Element Plus + ECharts
│   └── src/{views,components,api,router,types}
└── docs/                      # PRD / 数据字典 / schema 等
```

## 说明

- 自然语言解析为 **V1 本地规则解析器**（`nlp_parser.py`），结果需预览确认后保存；`ai_provider.py` 为付费 AI 抽象接口占位，默认不联网。
- 历史数据不含单品热量，食物 `kcal` 留空、`kcal_source='estimated'`；每日 `total_kcal_confirmed` 留空（符合数据字典）。
