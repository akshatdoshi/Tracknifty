"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    auth,
    feature_api,
    ingestion_api,
    portfolio_api,
    rules_api,
    webhook_api,
)
from app.config import settings
from app.db.base import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler
    init_db()
    from app.scheduler.tasks import start_scheduler

    _scheduler = start_scheduler()
    yield
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)


app = FastAPI(
    title="Tracknifty — BSH Recommendation Engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (
    auth, portfolio_api, feature_api, ingestion_api, rules_api, webhook_api,
):
    app.include_router(module.router)


@app.get("/api/health")
def health() -> dict:
    from app.pipeline.providers import get_price_provider

    return {
        "status": "ok",
        "price_provider": get_price_provider().name,
        "database": "postgresql" if settings.is_postgres else "sqlite",
        "scheduler": settings.scheduler if settings.enable_scheduler else "off",
    }
