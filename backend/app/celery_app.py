"""Celery wiring for the production stack.

Reuses the exact task callables from ``app.scheduler.tasks`` so behaviour is
identical to local APScheduler mode. Activated by running a Celery worker + beat
against the Redis broker (see docker-compose). When ``SCHEDULER != celery`` this
module is simply unused.
"""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.config import settings
from app.scheduler import tasks as jobs

broker = settings.redis_url or "redis://localhost:6379/0"
celery_app = Celery("tracknifty", broker=broker, backend=broker)
celery_app.conf.timezone = "Asia/Kolkata"


@celery_app.task(name="poll_live_prices")
def poll_live_prices() -> None:
    jobs.poll_live_prices()


@celery_app.task(name="daily_batch_score")
def daily_batch_score() -> None:
    jobs.daily_batch_score()


@celery_app.task(name="weekly_retrain")
def weekly_retrain() -> None:
    jobs.weekly_retrain()


celery_app.conf.beat_schedule = {
    "poll-live-prices": {
        "task": "poll_live_prices",
        "schedule": crontab(minute="*/15", hour="9-15", day_of_week="mon-fri"),
    },
    "daily-batch-score": {
        "task": "daily_batch_score",
        "schedule": crontab(minute=45, hour=15, day_of_week="mon-fri"),
    },
    "weekly-retrain": {
        "task": "weekly_retrain",
        "schedule": crontab(minute=0, hour=2, day_of_week="sun"),
    },
}
