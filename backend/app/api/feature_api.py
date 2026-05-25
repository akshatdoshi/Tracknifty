"""Feature API — exposes the computed feature vector per stock per date.

Consumed by the ML engine and useful for audit/debugging: it shows exactly what
the model saw for a given recommendation.
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_owned_portfolio
from app.db.base import get_db
from app.db.models import Holding, PeerMap, Portfolio
from app.features.engineering import PositionContext, build_feature_row
from app.pipeline.enrichment import latest_close, price_series

router = APIRouter(prefix="/api/features", tags=["features"])


@router.get("/{portfolio_id}/{ticker}")
def feature_vector(
    ticker: str,
    portfolio: Portfolio = Depends(get_owned_portfolio),
    db: Session = Depends(get_db),
) -> dict:
    ticker = ticker.upper()
    holding = db.scalars(
        select(Holding).where(
            Holding.portfolio_id == portfolio.id, Holding.ticker == ticker
        )
    ).first()
    if holding is None:
        raise HTTPException(status_code=404, detail="Holding not found")

    stock_series = price_series(db, ticker)
    if stock_series.empty:
        raise HTTPException(status_code=404, detail="No price data for ticker")
    bench_series = price_series(db, portfolio.benchmark_symbol)
    pm = db.scalars(select(PeerMap).where(PeerMap.ticker == ticker)).first()
    peer_series = (
        {p: price_series(db, p) for p in pm.peers if p != ticker} if pm else {}
    )

    as_of = stock_series.index[-1]
    close = latest_close(db, ticker) or holding.wac
    position = PositionContext(
        weight_pct=float("nan"),
        holding_days=(as_of - holding.first_buy_date).days if holding.first_buy_date else 0,
        unrealised_pnl_pct=(close / holding.wac - 1.0) * 100.0 if holding.wac else 0.0,
        derisked=holding.derisked,
    )
    bundle = build_feature_row(stock_series, bench_series, peer_series, as_of, position)
    return {
        "ticker": ticker,
        "as_of_date": as_of.isoformat() if isinstance(as_of, dt.date) else str(as_of),
        "features": bundle.features,
        "context": bundle.context,
    }
