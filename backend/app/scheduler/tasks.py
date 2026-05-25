"""Scheduled jobs (the doc's serving-layer scheduler).

Each job opens its own session. The same callables are reused whether they run
under in-process APScheduler (local) or Celery beat (production).
"""

from __future__ import annotations

import datetime as dt
import logging

from sqlalchemy import select

from app.db.base import SessionLocal
from app.db.models import PeerMap, Portfolio
from app.pipeline.providers import get_price_provider
from app.services.dashboard import invalidate
from app.services.scoring import score_all

logger = logging.getLogger(__name__)


def poll_live_prices() -> None:
    """Refresh the latest bar for every tracked symbol (every 15 min)."""
    provider = get_price_provider()
    from app.db.models import PriceBar

    with SessionLocal() as db:
        symbols = set()
        for pm in db.scalars(select(PeerMap)):
            symbols.add(pm.ticker)
            symbols.add(pm.benchmark_symbol)
            symbols.update(pm.peers)
        for symbol in symbols:
            bar = provider.get_latest(symbol)
            if bar is None:
                continue
            existing = db.scalars(
                select(PriceBar).where(
                    PriceBar.symbol == symbol, PriceBar.date == bar.date
                )
            ).first()
            if existing:
                existing.close = bar.close
            else:
                db.add(
                    PriceBar(
                        symbol=symbol, date=bar.date, open=bar.open, high=bar.high,
                        low=bar.low, close=bar.close, volume=bar.volume,
                    )
                )
        db.commit()
    logger.info("Live price poll complete")


def daily_batch_score() -> None:
    """End-of-day scoring run for all portfolios."""
    with SessionLocal() as db:
        written = score_all(db)
        for p in db.scalars(select(Portfolio)):
            invalidate(p.id)
    logger.info("Daily batch scoring wrote %d signals", written)


def weekly_retrain() -> None:
    from app.ml.train import train_model

    with SessionLocal() as db:
        try:
            mv = train_model(db)
            logger.info("Weekly retrain produced model %s", mv.version)
        except Exception as exc:  # not enough data, etc.
            logger.warning("Weekly retrain skipped: %s", exc)


def start_scheduler() -> object | None:
    """Start in-process APScheduler when configured for local mode."""
    from app.config import settings

    if not settings.enable_scheduler or settings.scheduler != "apscheduler":
        return None

    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    # Every 15 min during NSE market hours (Mon-Fri 09:15-15:30 IST).
    scheduler.add_job(
        poll_live_prices,
        CronTrigger(day_of_week="mon-fri", hour="9-15", minute="*/15"),
        id="poll_live_prices", replace_existing=True,
    )
    scheduler.add_job(
        daily_batch_score,
        CronTrigger(day_of_week="mon-fri", hour=15, minute=45),
        id="daily_batch_score", replace_existing=True,
    )
    scheduler.add_job(
        weekly_retrain,
        CronTrigger(day_of_week="sun", hour=2, minute=0),
        id="weekly_retrain", replace_existing=True,
    )
    scheduler.start()
    logger.info("APScheduler started (next score at %s)", dt.time(15, 45))
    return scheduler
