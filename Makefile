.PHONY: help install seed backend frontend test dev up down build clean

help:
	@echo "Tracknifty — BSH Recommendation Engine"
	@echo ""
	@echo "Local (lightweight) workflow:"
	@echo "  make install   Create backend venv + install deps, install frontend deps"
	@echo "  make seed      Generate demo data, train model, backfill signals (SQLite)"
	@echo "  make backend   Run FastAPI on :8000 (APScheduler, SQLite)"
	@echo "  make frontend  Run Vite dev server on :5173 (proxies /api to :8000)"
	@echo "  make test      Run backend pytest suite"
	@echo ""
	@echo "Production-shaped stack (Docker):"
	@echo "  make up        docker compose up (Postgres+TimescaleDB, Redis, Celery, ...)"
	@echo "  make down      docker compose down"

VENV := backend/.venv
PY := $(VENV)/bin/python

install:
	python3 -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r backend/requirements.txt
	cd frontend && npm install

seed:
	cd backend && .venv/bin/python -m seed.seed_data $(if $(FORCE),--force,)

backend:
	cd backend && .venv/bin/python -m uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && .venv/bin/python -m pytest -q

dev: seed
	@echo "Now run 'make backend' and 'make frontend' in two terminals."

up:
	docker compose up --build

down:
	docker compose down

clean:
	rm -f backend/tracknifty.db
	rm -rf backend/model_store
