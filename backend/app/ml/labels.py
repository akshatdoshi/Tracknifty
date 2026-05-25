"""Label construction + training-set assembly.

This is the single most important design decision in the project (per the
outline). Ground-truth labels are built from *forward* relative performance:

* **BUY**  if the stock beats its benchmark by more than ``buy_alpha_pct`` over
  the forward window,
* **SELL** if it lags by more than ``sell_alpha_pct``,
* **HOLD** otherwise.

The thresholds and window live in config and must be signed off by the
investment team before go-live.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import PeerMap, PriceBar
from app.features.engineering import FEATURE_NAMES, build_feature_row


def _full_series(db: Session, symbol: str) -> pd.Series:
    bars = list(
        db.scalars(
            select(PriceBar).where(PriceBar.symbol == symbol).order_by(PriceBar.date)
        )
    )
    if not bars:
        return pd.Series(dtype=float)
    return pd.Series([b.close for b in bars], index=[b.date for b in bars], dtype=float)


def label_for_alpha(alpha_pct: float) -> str:
    if alpha_pct > settings.label_buy_alpha_pct:
        return "BUY"
    if alpha_pct < settings.label_sell_alpha_pct:
        return "SELL"
    return "HOLD"


def build_training_frame(db: Session) -> tuple[np.ndarray, list[str], dict]:
    """Assemble (X, y, meta) by sampling historical dates across the universe."""
    peer_maps = list(db.scalars(select(PeerMap)))
    symbols = {pm.ticker for pm in peer_maps}
    for pm in peer_maps:
        symbols.add(pm.benchmark_symbol)
        symbols.update(pm.peers)
    series_map = {s: _full_series(db, s) for s in symbols}

    fwd = settings.label_forward_days
    X: list[list[float]] = []
    y: list[str] = []

    for pm in peer_maps:
        stock = series_map.get(pm.ticker)
        bench = series_map.get(pm.benchmark_symbol)
        if stock is None or stock.empty or bench is None or bench.empty:
            continue
        peer_series = {p: series_map[p] for p in pm.peers if p in series_map}
        dates = list(stock.index)

        # Sample roughly monthly, leaving room for the forward window.
        for i in range(252, len(dates) - fwd, 21):
            as_of = dates[i]
            future = dates[i + fwd]
            bundle = build_feature_row(stock, bench, peer_series, as_of, position=None)

            stock_fwd = stock.iloc[i + fwd] / stock.iloc[i] - 1.0
            bench_now = _asof(bench, as_of)
            bench_future = _asof(bench, future)
            if bench_now is None or bench_future is None or bench_now == 0:
                continue
            bench_fwd = bench_future / bench_now - 1.0
            alpha_pct = (stock_fwd - bench_fwd) * 100.0

            X.append(bundle.vector())
            y.append(label_for_alpha(alpha_pct))

    meta = {
        "feature_names": FEATURE_NAMES,
        "forward_days": fwd,
        "buy_alpha_pct": settings.label_buy_alpha_pct,
        "sell_alpha_pct": settings.label_sell_alpha_pct,
    }
    return np.array(X, dtype=float), y, meta


def _asof(series: pd.Series, when: dt.date) -> float | None:
    sub = series[series.index <= when]
    return float(sub.iloc[-1]) if len(sub) else None
