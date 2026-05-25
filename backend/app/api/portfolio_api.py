"""Portfolio API — holdings, weights, P&L and BSH signals for the dashboard."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    get_owned_portfolio,
    visible_portfolios,
)
from app.db.base import get_db
from app.db.models import Portfolio, User
from app.schemas import PortfolioOut, SignalOut
from app.services.dashboard import build_rows

router = APIRouter(prefix="/api/portfolios", tags=["portfolios"])


@router.get("", response_model=list[PortfolioOut])
def list_portfolios(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[PortfolioOut]:
    out = []
    for p in visible_portfolios(db, user):
        out.append(
            PortfolioOut(
                id=p.id, name=p.name, benchmark_symbol=p.benchmark_symbol,
                holdings_count=len(p.holdings),
            )
        )
    return out


@router.get("/{portfolio_id}/signals", response_model=list[SignalOut])
def portfolio_signals(
    portfolio: Portfolio = Depends(get_owned_portfolio),
    db: Session = Depends(get_db),
) -> list[SignalOut]:
    return build_rows(db, portfolio)


@router.get("/signals/global", response_model=list[SignalOut])
def global_signals(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[SignalOut]:
    """Consolidated view across every portfolio the user can see."""
    rows: list[SignalOut] = []
    for p in visible_portfolios(db, user):
        rows.extend(build_rows(db, p))
    return rows
