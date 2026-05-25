"""SQLAlchemy engine / session wiring.

A single `DATABASE_URL` drives everything. SQLite gets the `check_same_thread`
tweak it needs to play nicely with FastAPI's threadpool; everything else uses a
normal pooled engine.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


def _make_engine():
    if settings.database_url.startswith("sqlite"):
        return create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False},
            future=True,
        )
    return create_engine(settings.database_url, pool_pre_ping=True, future=True)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields a request-scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables (and TimescaleDB hypertables on Postgres)."""
    from app.db import models  # noqa: F401  (register mappers)
    from app.db.timeseries import setup_hypertables

    Base.metadata.create_all(bind=engine)
    setup_hypertables(engine)
