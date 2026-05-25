"""ORM models for the BSH engine.

The schema mirrors the solution outline: relational records (portfolios,
transactions, holdings, rules, signals, audit) plus a price time-series table
that becomes a TimescaleDB hypertable on Postgres.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="manager")  # manager | admin
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_utcnow)

    portfolios: Mapped[list["Portfolio"]] = relationship(back_populates="owner")


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    benchmark_symbol: Mapped[str] = mapped_column(String(32), default="^NSEI")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_utcnow)

    owner: Mapped[User] = relationship(back_populates="portfolios")
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )
    holdings: Mapped[list["Holding"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )
    rule: Mapped["Rule"] = relationship(
        back_populates="portfolio", uselist=False, cascade="all, delete-orphan"
    )


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint(
            "portfolio_id", "ticker", "trade_date", "side", "quantity", "price",
            name="uq_transaction_natural_key",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True)
    ticker: Mapped[str] = mapped_column(String(32), index=True)
    trade_date: Mapped[dt.date] = mapped_column(Date)
    side: Mapped[str] = mapped_column(String(4))  # BUY | SELL
    quantity: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    fees: Mapped[float] = mapped_column(Float, default=0.0)

    portfolio: Mapped[Portfolio] = relationship(back_populates="transactions")


class Holding(Base):
    """Current position, recomputed from the transaction ledger."""

    __tablename__ = "holdings"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "ticker", name="uq_holding"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True)
    ticker: Mapped[str] = mapped_column(String(32), index=True)
    sector: Mapped[str] = mapped_column(String(64), default="Unknown")
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    wac: Mapped[float] = mapped_column(Float, default=0.0)  # weighted average cost
    first_buy_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    derisked: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_utcnow)

    portfolio: Mapped[Portfolio] = relationship(back_populates="holdings")


class PriceBar(Base):
    """Daily OHLCV for any symbol (stock, benchmark or peer)."""

    __tablename__ = "price_bars"
    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_price_bar"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    date: Mapped[dt.date] = mapped_column(Date, index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float, default=0.0)


class PeerMap(Base):
    """One row per ticker: its sector, benchmark and sector peers."""

    __tablename__ = "peer_maps"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    sector: Mapped[str] = mapped_column(String(64))
    benchmark_symbol: Mapped[str] = mapped_column(String(32), default="^NSEI")
    peers: Mapped[list] = mapped_column(JSON, default=list)


class Rule(Base):
    """Per-portfolio guardrails, editable from the UI."""

    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id"), unique=True, index=True
    )
    min_weight_pct: Mapped[float] = mapped_column(Float, default=10.0)
    max_weight_pct: Mapped[float] = mapped_column(Float, default=15.0)
    momentum_threshold_pct: Mapped[float] = mapped_column(Float, default=5.0)
    volatility_ceiling: Mapped[float] = mapped_column(Float, default=1.5)
    confidence_floor: Mapped[float] = mapped_column(Float, default=60.0)
    derisk_override: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_utcnow)

    portfolio: Mapped[Portfolio] = relationship(back_populates="rule")


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    artifact_path: Mapped[str] = mapped_column(String(512))
    feature_list: Mapped[list] = mapped_column(JSON, default=list)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    n_samples: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_utcnow)


class Signal(Base):
    __tablename__ = "signals"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "ticker", "as_of_date", name="uq_signal"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True)
    ticker: Mapped[str] = mapped_column(String(32), index=True)
    as_of_date: Mapped[dt.date] = mapped_column(Date, index=True)
    signal: Mapped[str] = mapped_column(String(4))       # BUY | SELL | HOLD
    raw_signal: Mapped[str] = mapped_column(String(4))   # model output pre-rules
    confidence: Mapped[float] = mapped_column(Float)     # 0-100
    drivers: Mapped[list] = mapped_column(JSON, default=list)
    explanation: Mapped[str] = mapped_column(String(512), default="")
    rule_notes: Mapped[list] = mapped_column(JSON, default=list)
    model_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("model_versions.id"), nullable=True
    )
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_utcnow)


class IngestionLog(Base):
    __tablename__ = "ingestion_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(64))
    filename: Mapped[str] = mapped_column(String(256), default="")
    status: Mapped[str] = mapped_column(String(16))  # SUCCESS | QUARANTINED | PARTIAL
    rows_total: Mapped[int] = mapped_column(Integer, default=0)
    rows_ingested: Mapped[int] = mapped_column(Integer, default=0)
    rows_skipped: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_utcnow)


class RuleAuditLog(Base):
    __tablename__ = "rule_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    parameter: Mapped[str] = mapped_column(String(64))
    old_value: Mapped[str] = mapped_column(String(64))
    new_value: Mapped[str] = mapped_column(String(64))
    changed_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_utcnow)
