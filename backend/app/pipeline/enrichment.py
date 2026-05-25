"""Stages 3 & 4 — enrichment + storage orchestration.

Turns the validated transaction ledger into current holdings (quantity, WAC,
de-risk flag) and provides the live-price join used to compute market value and
unrealised P&L for the dashboard.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Holding, IngestionLog, PeerMap, PriceBar, Transaction
from app.pipeline.validation import ValidationResult


def ingest_transactions(
    db: Session,
    portfolio_id: int,
    result: ValidationResult,
    filename: str,
    source: str = "upload",
) -> IngestionLog:
    """Persist validated rows (skipping duplicates) and log the outcome."""
    if result.quarantined:
        log = IngestionLog(
            source=source, filename=filename, status="QUARANTINED",
            rows_total=result.rows_total, rows_ingested=0,
            rows_skipped=result.rows_total, errors=result.errors[:200],
        )
        db.add(log)
        db.commit()
        return log

    existing = {
        (t.ticker, t.trade_date, t.side, t.quantity, t.price)
        for t in db.scalars(
            select(Transaction).where(Transaction.portfolio_id == portfolio_id)
        )
    }

    ingested = skipped = 0
    for _, row in result.clean.iterrows():
        key = (row["ticker"], row["trade_date"], row["side"],
               float(row["quantity"]), float(row["price"]))
        if key in existing:
            skipped += 1
            continue
        db.add(
            Transaction(
                portfolio_id=portfolio_id, ticker=row["ticker"],
                trade_date=row["trade_date"], side=row["side"],
                quantity=float(row["quantity"]), price=float(row["price"]),
                fees=float(row.get("fees") or 0.0),
            )
        )
        existing.add(key)
        ingested += 1
    db.commit()

    rebuild_holdings(db, portfolio_id)

    status = "SUCCESS" if result.rows_rejected == 0 else "PARTIAL"
    log = IngestionLog(
        source=source, filename=filename, status=status,
        rows_total=result.rows_total, rows_ingested=ingested,
        rows_skipped=skipped + result.rows_rejected, errors=result.errors[:200],
    )
    db.add(log)
    db.commit()
    return log


def rebuild_holdings(db: Session, portfolio_id: int) -> None:
    """Recompute holdings from the full transaction ledger (WAC + de-risk)."""
    txns = list(
        db.scalars(
            select(Transaction)
            .where(Transaction.portfolio_id == portfolio_id)
            .order_by(Transaction.trade_date, Transaction.id)
        )
    )
    sectors = {p.ticker: p.sector for p in db.scalars(select(PeerMap))}

    positions: dict[str, dict] = {}
    for t in txns:
        pos = positions.setdefault(
            t.ticker,
            {"qty": 0.0, "cost": 0.0, "first_buy": None, "derisked": False},
        )
        if t.side == "BUY":
            pos["cost"] += t.quantity * t.price + t.fees
            pos["qty"] += t.quantity
            if pos["first_buy"] is None:
                pos["first_buy"] = t.trade_date
        else:  # SELL
            wac = pos["cost"] / pos["qty"] if pos["qty"] > 0 else 0.0
            sold = min(t.quantity, pos["qty"])
            pos["qty"] -= sold
            pos["cost"] -= sold * wac
            if pos["qty"] > 1e-6:  # partial exit while still holding => de-risk
                pos["derisked"] = True

    # Replace existing holdings for this portfolio.
    for h in db.scalars(
        select(Holding).where(Holding.portfolio_id == portfolio_id)
    ):
        db.delete(h)

    for ticker, pos in positions.items():
        if pos["qty"] <= 1e-6:
            continue
        db.add(
            Holding(
                portfolio_id=portfolio_id, ticker=ticker,
                sector=sectors.get(ticker, "Unknown"),
                quantity=round(pos["qty"], 4),
                wac=round(pos["cost"] / pos["qty"], 4) if pos["qty"] else 0.0,
                first_buy_date=pos["first_buy"], derisked=pos["derisked"],
                updated_at=dt.datetime.now(dt.timezone.utc),
            )
        )
    db.commit()


def latest_close(db: Session, symbol: str, on_or_before: dt.date | None = None) -> float | None:
    stmt = select(PriceBar).where(PriceBar.symbol == symbol)
    if on_or_before is not None:
        stmt = stmt.where(PriceBar.date <= on_or_before)
    bar = db.scalars(stmt.order_by(PriceBar.date.desc()).limit(1)).first()
    return bar.close if bar else None


def price_series(db: Session, symbol: str, lookback_days: int = 400) -> pd.Series:
    """Close-price series indexed by date, oldest first."""
    bars = list(
        db.scalars(
            select(PriceBar)
            .where(PriceBar.symbol == symbol)
            .order_by(PriceBar.date.desc())
            .limit(lookback_days)
        )
    )
    bars.reverse()
    if not bars:
        return pd.Series(dtype=float)
    return pd.Series(
        [b.close for b in bars], index=[b.date for b in bars], dtype=float
    )
