# Weight Health App — one-click dev / ops
# Uses the managed Python & Node runtimes by default; override with env vars.

PY      ?= /Users/wuzhe/.workbuddy/binaries/python/envs/default/bin/python
NPM     ?= /Users/wuzhe/.workbuddy/binaries/node/versions/22.22.2/bin/npm
ROOT    := $(CURDIR)
BACKEND := $(ROOT)/backend
FRONTEND:= $(ROOT)/frontend
PORT_BE := 8011
PORT_FE := 5173

.PHONY: help install backend frontend import test dev

help:
	@echo "Targets:"
	@echo "  install   - install backend (pip) + frontend (npm) deps"
	@echo "  backend   - run FastAPI on :$(PORT_BE)"
	@echo "  frontend  - run Vite dev on :$(PORT_FE) (proxies /api -> :$(PORT_BE))"
	@echo "  import    - import historical seed data into SQLite (idempotent)"
	@echo "  test      - run backend import/idempotency test"
	@echo "  dev       - run backend + frontend together"

install:
	cd $(BACKEND)  && $(PY) -m pip install -r requirements.txt
	cd $(FRONTEND) && $(NPM) install

backend:
	cd $(BACKEND) && $(PY) -m uvicorn app.main:app --host 127.0.0.1 --port $(PORT_BE) --reload

frontend:
	cd $(FRONTEND) && $(NPM) run dev -- --port $(PORT_FE) --host

import:
	cd $(BACKEND) && $(PY) -c "from app.db import init_db; from app.services.history_importer import import_history; init_db(); print(import_history())"

test:
	cd $(BACKEND) && $(PY) tests/test_import.py

dev:
	@echo "Starting backend (:$(PORT_BE)) + frontend (:$(PORT_FE))..."
	@bash start.sh
