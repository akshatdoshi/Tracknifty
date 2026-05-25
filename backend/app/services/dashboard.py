"""Assembles the per-stock rows the dashboard renders.

Combines each holding with its latest signal, position metrics, display returns
and a short weekly signal trace. Results are cached briefly to keep reads fast.
"""

from __future__ import annotations

import datetime as dt
import math

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache import cache
from app.db.models import Holding, PeerMap, Portfolio, Signal
from app.pipeline.enrichment import latest_close, price_series
from app.schemas import Driver, SignalOut

_WINDOW_1M = 21
_WINDOW_3M = 63


def _pct_return(series, window: int) -> float | None:
    if len(series) <= window:
        return None
    base = series.iloc[-1 - window]
    return float((series.iloc[-1] / base - 1.0) * 100.0) if base else None


def _clean(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return value


def build_rows(db: Session, portfolio: Portfolio) -> list[SignalOut]:
    cache_key = f"rows:{portfolio.id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return [SignalOut(**row) for row in cached]

    holdings = list(
        db.scalars(select(Holding).where(Holding.portfolio_id == portfolio.id))
    )
    peer_lookup = {p.ticker: p for p in db.scalars(select(PeerMap))}
    bench_series = price_series(db, portfolio.benchmark_symbol)
    bench_3m = _pct_return(bench_series, _WINDOW_3M)

    market_values = {}
    for h in holdings:
        close = latest_close(db, h.ticker)
        market_values[h.ticker] = (close or h.wac) * h.quantity
    total_mv = sum(market_values.values()) or 1.0

    rows: list[SignalOut] = []
    for h in holdings:
        series = price_series(db, h.ticker)
        close = latest_close(db, h.ticker)
        weight_pct = 100.0 * market_values[h.ticker] / total_mv
        ret_1m = _pct_return(series, _WINDOW_1M)
        stock_3m = _pct_return(series, _WINDOW_3M)
        alpha = (
            stock_3m - bench_3m
            if stock_3m is not None and bench_3m is not None else None
        )

        latest, trace = _latest_signal_and_trace(db, portfolio.id, h.ticker)
        unrealised = (close / h.wac - 1.0) * 100.0 if (close and h.wac) else None
        holding_days = (dt.date.today() - h.first_buy_date).days if h.first_buy_date else 0

        rows.append(
            SignalOut(
                ticker=h.ticker, sector=h.sector, portfolio_id=portfolio.id,
                portfolio_name=portfolio.name, weight_pct=round(weight_pct, 2),
                ret_1m_pct=round(ret_1m, 2) if ret_1m is not None else None,
                alpha_pct=round(alpha, 2) if alpha is not None else None,
                confidence=latest.confidence if latest else 0.0,
                signal=latest.signal if latest else "HOLD",
                raw_signal=latest.raw_signal if latest else "HOLD",
                breach_min=weight_pct < (portfolio.rule.min_weight_pct if portfolio.rule else 10.0),
                breach_max=weight_pct > (portfolio.rule.max_weight_pct if portfolio.rule else 15.0),
                as_of_date=latest.as_of_date if latest else None,
                drivers=[Driver(**d) for d in (latest.drivers if latest else [])],
                explanation=latest.explanation if latest else "",
                rule_notes=latest.rule_notes if latest else [],
                quantity=h.quantity, wac=h.wac,
                current_price=round(close, 2) if close else None,
                unrealised_pnl_pct=round(unrealised, 2) if unrealised is not None else None,
                holding_days=holding_days, derisked=h.derisked,
                signal_trace=trace,
            )
        )

    cache.set(cache_key, [r.model_dump(mode="json") for r in rows])
    return rows


def _latest_signal_and_trace(db: Session, portfolio_id: int, ticker: str):
    signals = list(
        db.scalars(
            select(Signal)
            .where(Signal.portfolio_id == portfolio_id, Signal.ticker == ticker)
            .order_by(Signal.as_of_date.desc())
            .limit(4)
        )
    )
    latest = signals[0] if signals else None
    trace = [s.signal for s in reversed(signals)]  # oldest -> newest
    return latest, trace


def invalidate(portfolio_id: int) -> None:
    cache.set(f"rows:{portfolio_id}", None, ttl=1)
