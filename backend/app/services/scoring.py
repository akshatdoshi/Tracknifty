"""Batch scoring service.

For each holding it assembles the live feature vector (with position context),
runs the model, applies the portfolio's guardrails, and upserts a dated
``Signal`` row. This is what the scheduler triggers daily and what the webhook
endpoint runs on demand.
"""

from __future__ import annotations

import datetime as dt
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Holding, PeerMap, Portfolio, Rule, Signal
from app.features.engineering import PositionContext, build_feature_row
from app.ml.registry import load_latest
from app.pipeline.enrichment import latest_close, price_series
from app.rules.engine import apply_rules
from app.ml.score import predict

logger = logging.getLogger(__name__)


def score_all(db: Session, as_of: dt.date | None = None) -> int:
    """Score every portfolio; returns the number of signals written."""
    total = 0
    for portfolio in db.scalars(select(Portfolio)):
        total += score_portfolio(db, portfolio, as_of=as_of)
    return total


def score_portfolio(
    db: Session, portfolio: Portfolio, as_of: dt.date | None = None
) -> int:
    loaded = load_latest(db)
    if loaded is None:
        logger.warning("No trained model available; skipping scoring")
        return 0
    booster, mv = loaded
    classes = mv.metrics.get("classes", ["BUY", "HOLD", "SELL"])

    rule = db.scalars(
        select(Rule).where(Rule.portfolio_id == portfolio.id)
    ).first() or Rule(portfolio_id=portfolio.id)

    holdings = list(
        db.scalars(select(Holding).where(Holding.portfolio_id == portfolio.id))
    )
    if not holdings:
        return 0

    peer_lookup = {p.ticker: p for p in db.scalars(select(PeerMap))}
    bench_series = price_series(db, portfolio.benchmark_symbol)

    # First pass: market values for portfolio weights.
    market_values: dict[str, float] = {}
    for h in holdings:
        close = latest_close(db, h.ticker, as_of)
        market_values[h.ticker] = (close or h.wac) * h.quantity
    total_mv = sum(market_values.values()) or 1.0

    written = 0
    for h in holdings:
        stock_series = price_series(db, h.ticker)
        if stock_series.empty:
            continue
        effective_as_of = as_of or stock_series.index[-1]

        pm = peer_lookup.get(h.ticker)
        peer_series = {}
        if pm:
            peer_series = {
                p: price_series(db, p) for p in pm.peers if p != h.ticker
            }

        close = latest_close(db, h.ticker, as_of) or h.wac
        weight_pct = 100.0 * market_values[h.ticker] / total_mv
        holding_days = (
            (effective_as_of - h.first_buy_date).days if h.first_buy_date else 0
        )
        unrealised_pnl_pct = (close / h.wac - 1.0) * 100.0 if h.wac else 0.0

        position = PositionContext(
            weight_pct=weight_pct, holding_days=holding_days,
            unrealised_pnl_pct=unrealised_pnl_pct, derisked=h.derisked,
        )
        bundle = build_feature_row(
            stock_series, bench_series, peer_series, effective_as_of, position
        )
        prediction = predict(booster, classes, bundle.vector())
        outcome = apply_rules(prediction, bundle.context, rule)

        _upsert_signal(
            db, portfolio.id, h.ticker, effective_as_of, prediction, outcome, mv.id
        )
        written += 1

    db.commit()
    logger.info("Scored portfolio '%s': %d signals", portfolio.name, written)
    return written


def _upsert_signal(db, portfolio_id, ticker, as_of, prediction, outcome, model_version_id):
    existing = db.scalars(
        select(Signal).where(
            Signal.portfolio_id == portfolio_id,
            Signal.ticker == ticker,
            Signal.as_of_date == as_of,
        )
    ).first()
    payload = dict(
        signal=outcome.signal, raw_signal=prediction.signal,
        confidence=outcome.confidence, drivers=prediction.drivers,
        explanation=prediction.explanation, rule_notes=outcome.notes,
        model_version_id=model_version_id,
    )
    if existing:
        for k, v in payload.items():
            setattr(existing, k, v)
    else:
        db.add(
            Signal(
                portfolio_id=portfolio_id, ticker=ticker, as_of_date=as_of, **payload
            )
        )
