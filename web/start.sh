#!/usr/bin/env bash
# Start backend (FastAPI :8011) and frontend (Vite :5173) together.
# Vite proxies /api -> http://127.0.0.1:8011
set -e

PY="${PY:-/Users/wuzhe/.workbuddy/binaries/python/envs/default/bin/python}"
NPM="${NPM:-/Users/wuzhe/.workbuddy/binaries/node/versions/22.22.2/bin/npm}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Ensure DB + seed import before serving
echo "==> Ensuring SQLite schema + idempotent history import"
( cd "$ROOT/backend" && "$PY" -c "from app.db import init_db; from app.services.history_importer import import_history; init_db(); r=import_history(); print('imported=%s skipped=%s' % (r['inserted'], r['skipped']))" )

echo "==> Starting backend on :8011"
( cd "$ROOT/backend" && "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8011 --reload ) &
BE_PID=$!

echo "==> Starting frontend on :5173 (Vite dev server)"
( cd "$ROOT/frontend" && "$NPM" run dev -- --port 5173 --host ) &
FE_PID=$!

trap 'kill $BE_PID $FE_PID 2>/dev/null || true' EXIT INT TERM
wait
