"""TimescaleDB hypertable setup.

On Postgres this turns ``price_bars`` into a hypertable (the doc's TimescaleDB
requirement). On SQLite — the default local mode — it is a silent no-op so the
exact same code path runs everywhere.
"""

from __future__ import annotations

import logging

from sqlalchemy import Engine, text

logger = logging.getLogger(__name__)


def setup_hypertables(engine: Engine) -> None:
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
        # ``if_not_exists`` + ``migrate_data`` makes this safe to re-run.
        conn.execute(
            text(
                "SELECT create_hypertable('price_bars', 'date', "
                "if_not_exists => TRUE, migrate_data => TRUE)"
            )
        )
    logger.info("TimescaleDB hypertable ensured on price_bars")
