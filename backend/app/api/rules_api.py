"""Rules API — per-portfolio guardrail config with full change audit."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_portfolio
from app.db.base import get_db
from app.db.models import Portfolio, Rule, RuleAuditLog, User
from app.schemas import RuleOut, RuleUpdate
from app.services.dashboard import invalidate

router = APIRouter(prefix="/api/portfolios", tags=["rules"])


def _get_or_create_rule(db: Session, portfolio_id: int) -> Rule:
    rule = db.scalars(select(Rule).where(Rule.portfolio_id == portfolio_id)).first()
    if rule is None:
        rule = Rule(portfolio_id=portfolio_id)
        db.add(rule)
        db.commit()
        db.refresh(rule)
    return rule


@router.get("/{portfolio_id}/rules", response_model=RuleOut)
def get_rules(
    portfolio: Portfolio = Depends(get_owned_portfolio),
    db: Session = Depends(get_db),
) -> Rule:
    return _get_or_create_rule(db, portfolio.id)


@router.put("/{portfolio_id}/rules", response_model=RuleOut)
def update_rules(
    update: RuleUpdate,
    portfolio: Portfolio = Depends(get_owned_portfolio),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Rule:
    rule = _get_or_create_rule(db, portfolio.id)
    for field, new_value in update.model_dump(exclude_unset=True).items():
        old_value = getattr(rule, field)
        if old_value == new_value:
            continue
        db.add(
            RuleAuditLog(
                portfolio_id=portfolio.id, user_id=user.id, parameter=field,
                old_value=str(old_value), new_value=str(new_value),
            )
        )
        setattr(rule, field, new_value)
    db.commit()
    db.refresh(rule)
    invalidate(portfolio.id)  # next read reflects new guardrails immediately
    return rule


@router.get("/{portfolio_id}/rules/audit")
def rules_audit(
    portfolio: Portfolio = Depends(get_owned_portfolio),
    db: Session = Depends(get_db),
) -> list[dict]:
    logs = db.scalars(
        select(RuleAuditLog)
        .where(RuleAuditLog.portfolio_id == portfolio.id)
        .order_by(RuleAuditLog.changed_at.desc())
    )
    return [
        {
            "parameter": log.parameter, "old_value": log.old_value,
            "new_value": log.new_value, "user_id": log.user_id,
            "changed_at": log.changed_at,
        }
        for log in logs
    ]
