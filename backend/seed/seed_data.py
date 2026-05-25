"""Seed a fully working demo: users, universe, prices, portfolios, model, signals.

Run with ``python -m seed.seed_data``. Idempotent-ish: price history (the
expensive part) is only generated when the table is empty; pass ``--force`` to
wipe and rebuild everything.
"""

from __future__ import annotations

import datetime as dt
import logging
import sys

from sqlalchemy import delete, func, select

from app.db.base import SessionLocal, init_db
from app.db.models import (
    Holding, IngestionLog, ModelVersion, PeerMap, Portfolio, PriceBar, Rule,
    RuleAuditLog, Signal, Transaction, User,
)
from app.pipeline.enrichment import rebuild_holdings
from app.pipeline.providers import get_price_provider
from app.security import hash_password
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")

BENCHMARK = "^NSEI"
UNIVERSE = {
    "IT": ["INFY.NS", "TCS.NS", "WIPRO.NS", "HCLTECH.NS"],
    "Banking": ["HDFCBANK.NS", "ICICIBANK.NS", "AXISBANK.NS", "SBIN.NS"],
    "Auto": ["TATAMOTORS.NS", "MARUTI.NS", "M&M.NS"],
    "FMCG": ["HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS"],
    "Pharma": ["SUNPHARMA.NS", "CIPLA.NS", "DRREDDY.NS"],
}
PORTFOLIOS = {
    "Alpha Fund": ["INFY.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS",
                   "TATAMOTORS.NS", "HINDUNILVR.NS", "SUNPHARMA.NS"],
    "Beta Fund": ["WIPRO.NS", "HCLTECH.NS", "AXISBANK.NS", "SBIN.NS",
                  "MARUTI.NS", "ITC.NS", "CIPLA.NS"],
}


def _wipe(db) -> None:
    for model in (
        Signal, RuleAuditLog, Rule, Holding, Transaction, IngestionLog,
        ModelVersion, Portfolio, PeerMap, PriceBar, User,
    ):
        db.execute(delete(model))
    db.commit()


def seed(force: bool = False) -> None:
    init_db()
    with SessionLocal() as db:
        if force:
            _wipe(db)

        if db.scalar(select(func.count(User.id))):
            logger.info("Users already present — use --force to reseed. Skipping.")
            return

        admin = User(username="admin", hashed_password=hash_password("admin123"), role="admin")
        m1 = User(username="manager1", hashed_password=hash_password("manager123"), role="manager")
        m2 = User(username="manager2", hashed_password=hash_password("manager123"), role="manager")
        db.add_all([admin, m1, m2])
        db.commit()

        _seed_peer_maps(db)
        _seed_prices(db)

        owners = {"Alpha Fund": m1, "Beta Fund": m2}
        for name, tickers in PORTFOLIOS.items():
            portfolio = Portfolio(name=name, owner_id=owners[name].id, benchmark_symbol=BENCHMARK)
            db.add(portfolio)
            db.commit()
            db.refresh(portfolio)
            db.add(
                Rule(
                    portfolio_id=portfolio.id,
                    min_weight_pct=settings.default_min_weight_pct,
                    max_weight_pct=settings.default_max_weight_pct,
                    momentum_threshold_pct=settings.default_momentum_threshold_pct,
                    volatility_ceiling=settings.default_volatility_ceiling,
                    confidence_floor=settings.default_confidence_floor,
                    derisk_override=settings.default_derisk_override,
                )
            )
            _seed_transactions(db, portfolio, tickers)
            rebuild_holdings(db, portfolio.id)
        db.commit()

        _train_and_score(db)
    logger.info("Seed complete. Logins: admin/admin123, manager1/manager123, manager2/manager123")


def _seed_peer_maps(db) -> None:
    for sector, tickers in UNIVERSE.items():
        for ticker in tickers:
            db.add(
                PeerMap(
                    ticker=ticker, sector=sector, benchmark_symbol=BENCHMARK,
                    peers=[t for t in tickers if t != ticker],
                )
            )
    db.commit()
    logger.info("Seeded peer maps for %d sectors", len(UNIVERSE))


def _seed_prices(db) -> None:
    if db.scalar(select(func.count(PriceBar.id))):
        logger.info("Price bars already present; skipping price generation")
        return
    provider = get_price_provider()
    end = dt.date.today()
    start = end - dt.timedelta(days=365 * settings.price_history_years)
    symbols = {BENCHMARK}
    for tickers in UNIVERSE.values():
        symbols.update(tickers)

    for symbol in sorted(symbols):
        bars = provider.get_history(symbol, start, end)
        db.bulk_save_objects(
            [
                PriceBar(
                    symbol=symbol, date=b.date, open=b.open, high=b.high,
                    low=b.low, close=b.close, volume=b.volume,
                )
                for b in bars
            ]
        )
        db.commit()
        logger.info("  %s: %d bars (%s)", symbol, len(bars), provider.name)


def _close_on(db, symbol: str, on: dt.date) -> float:
    bar = db.scalars(
        select(PriceBar)
        .where(PriceBar.symbol == symbol, PriceBar.date <= on)
        .order_by(PriceBar.date.desc())
        .limit(1)
    ).first()
    return bar.close if bar else 100.0


def _seed_transactions(db, portfolio: Portfolio, tickers: list[str]) -> None:
    today = dt.date.today()
    buy_dates = [today - dt.timedelta(days=d) for d in (720, 400, 180)]
    for i, ticker in enumerate(tickers):
        qty = 100 + (i % 4) * 50
        for j, bd in enumerate(buy_dates):
            db.add(
                Transaction(
                    portfolio_id=portfolio.id, ticker=ticker, trade_date=bd,
                    side="BUY", quantity=qty, price=_close_on(db, ticker, bd), fees=20.0,
                )
            )
        # De-risk a couple of names: partial exit 90 days ago.
        if i % 3 == 0:
            exit_date = today - dt.timedelta(days=90)
            db.add(
                Transaction(
                    portfolio_id=portfolio.id, ticker=ticker, trade_date=exit_date,
                    side="SELL", quantity=qty, price=_close_on(db, ticker, exit_date),
                    fees=20.0,
                )
            )
    db.commit()


def _train_and_score(db) -> None:
    from app.ml.train import train_model
    from app.services.scoring import score_portfolio

    logger.info("Training model ...")
    mv = train_model(db)
    logger.info("Model %s trained: %s", mv.version, mv.metrics)

    # Backfill four weekly signals per portfolio so the trace sparkline has data.
    latest = db.scalar(select(func.max(PriceBar.date)))
    as_of_dates = [latest - dt.timedelta(days=7 * k) for k in (3, 2, 1, 0)]
    for portfolio in db.scalars(select(Portfolio)):
        for as_of in as_of_dates:
            score_portfolio(db, portfolio, as_of=as_of)
    logger.info("Scoring backfill complete")


if __name__ == "__main__":
    seed(force="--force" in sys.argv)
