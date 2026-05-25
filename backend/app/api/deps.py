"""Shared API dependencies: current user, RBAC, portfolio isolation."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import Portfolio, User
from app.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    cred_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))
    except Exception:
        raise cred_error
    user = db.get(User, user_id)
    if user is None:
        raise cred_error
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def get_owned_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Portfolio:
    """Fetch a portfolio, enforcing that a manager only sees their own."""
    portfolio = db.get(Portfolio, portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if user.role != "admin" and portfolio.owner_id != user.id:
        # Do not leak existence of other portfolios.
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


def visible_portfolios(db: Session, user: User) -> list[Portfolio]:
    from sqlalchemy import select

    stmt = select(Portfolio)
    if user.role != "admin":
        stmt = stmt.where(Portfolio.owner_id == user.id)
    return list(db.scalars(stmt))
