# Tracknifty — AI-Driven Buy / Sell / Hold Recommendation Engine

A **decision-support tool** for equity portfolio managers. It ingests portfolio
transactions and market prices, engineers features, trains an explainable
gradient-boosting model, applies per-portfolio guardrails, and serves
Buy / Sell / Hold signals — each with SHAP-based driver explanations — to a React
dashboard. **It does not place trades; every final investment decision stays with
the user.**

This is the **Phase 1** implementation of the First Water Global solution outline.

---

## Two ways to run, one codebase

Infrastructure is selected entirely through environment variables, so the same
code runs:

| | Local (default) | Production-shaped (Docker) |
|---|---|---|
| Database | SQLite | Postgres + TimescaleDB |
| Cache | in-memory TTL | Redis |
| Scheduler | in-process APScheduler | Celery worker + beat |
| Prices | yfinance → synthetic fallback | yfinance → synthetic fallback |
| Model store | local dir | local dir / S3 |

> **Price data:** the production price source is **yfinance**. When Yahoo Finance
> is unreachable (e.g. a sandbox without outbound access), the provider
> **automatically falls back to a deterministic synthetic generator** so the
> system always runs. `GET /api/health` reports which provider is active.

---

## Quickstart (local, no Docker)

```bash
make install      # backend venv + deps, frontend deps
make seed         # demo data + trained model + backfilled signals (SQLite)
make backend      # FastAPI on http://localhost:8000  (API docs at /docs)
make frontend     # Vite dev server on http://localhost:5173
```

Open http://localhost:5173 and log in:

| User | Password | Role |
|---|---|---|
| `admin` | `admin123` | admin (sees all portfolios, data-quality, re-score) |
| `manager1` | `manager123` | manager (Alpha Fund only) |
| `manager2` | `manager123` | manager (Beta Fund only) |

Run the tests with `make test`.

## Quickstart (production-shaped stack)

```bash
make up           # docker compose: db, redis, backend, worker, beat, frontend
```

Frontend on http://localhost:8080, API on http://localhost:8000. The backend
seeds itself on first boot.

---

## How it works

```
Upload / API → Ingestion → Validation (+quarantine) → Enrichment → Storage
                                                                      │
                          Feature engineering ◄──────────────────────┘
                                   │
        Labels (forward alpha) → XGBoost (versioned) → Score + SHAP
                                                          │
                              Rules / guardrails → BSH signal → Dashboard
```

- **Pipeline** (`app/pipeline/`): strict schema contract, per-row validation,
  duplicate skipping, gap detection, and an error-quarantine path that feeds the
  admin data-quality view. WAC and de-risk status are derived from the ledger.
- **Features** (`app/features/engineering.py`): four groups — Position, Momentum,
  Relative performance, Risk (15 features total).
- **Model** (`app/ml/`): labels from forward relative return
  (BUY/SELL/HOLD); XGBoost multiclass; every model is **versioned** and every
  signal records the `model_version_id` that produced it. SHAP (TreeSHAP)
  yields the top drivers + a plain-English summary.
- **Rules** (`app/rules/engine.py`): per-portfolio guardrails (min/max weight,
  momentum threshold, volatility ceiling, confidence floor, de-risk override).
  Guardrails only make signals more conservative and are read at scoring time, so
  UI edits take effect on the next run with no deploy.
- **API** (`app/api/`): JWT auth with `manager`/`admin` roles and strict
  portfolio isolation (a manager can never see another's portfolio). Routers:
  auth, portfolios/signals, features, ingestion (+data quality), rules (+audit),
  webhook/scheduler (+model versions).

### Label construction — needs sign-off

The most important design decision. Defaults (in `app/config.py`):

- **BUY** if forward 3-month return beats the benchmark by **> +5%**
- **SELL** if it lags by **> −5%**
- **HOLD** otherwise

`LABEL_FORWARD_DAYS`, `LABEL_BUY_ALPHA_PCT`, `LABEL_SELL_ALPHA_PCT` are
configurable and **must be agreed with the investment team before go-live**.

---

## Phase 1 exit criteria → where it lives

- Pipeline ingests & validates without manual intervention → `app/pipeline/`
- Live prices update every 15 min in market hours → `poll_live_prices` job
- BSH signals for 100% of active holdings → `services/scoring.py`
- ≥2 SHAP drivers per signal → `ml/explain.py` (verified in tests)
- Rule changes take effect next run, no deploy → `rules_api.py` + scoring-time read

## Project layout

```
backend/
  app/
    config.py            # env-driven dual-mode config
    db/                  # ORM models, engine, TimescaleDB hypertable (Postgres)
    pipeline/            # ingestion, validation, enrichment, price providers
    features/            # feature engineering
    ml/                  # labels, train, score, explain (SHAP), registry
    rules/               # guardrail engine
    services/            # scoring + dashboard assembly
    api/                 # FastAPI routers, auth, deps (RBAC + isolation)
    scheduler/           # APScheduler jobs (shared with Celery)
    celery_app.py        # Celery worker/beat for the production stack
  seed/seed_data.py      # demo universe, prices, portfolios, model, signals
  tests/                 # pytest (pipeline, features, rules, API)
  alembic/               # migrations (production Postgres)
frontend/                # React + Vite + TS + Tailwind + Recharts
docker-compose.yml       # full stack
```

## Out of scope (later phases)

LSTM/sequence model, the backtesting module, and the new-ideas similarity engine
are Phase 2/3 per the outline and are intentionally not implemented here.
