"""Webhook / scheduler API — trigger scoring & retraining on demand."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.base import get_db
from app.db.models import ModelVersion, Portfolio
from app.ml.train import train_model
from app.schemas import ModelVersionOut
from app.services.dashboard import invalidate
from app.services.scoring import score_all

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["scheduler"])


@router.post("/webhook/score", dependencies=[Depends(require_admin)])
def trigger_scoring(db: Session = Depends(get_db)) -> dict:
    written = score_all(db)
    for p in db.scalars(select(Portfolio)):
        invalidate(p.id)
    logger.info("Manual scoring run wrote %d signals", written)
    return {"status": "ok", "signals_written": written}


@router.post("/webhook/retrain", dependencies=[Depends(require_admin)])
def trigger_retrain(db: Session = Depends(get_db)) -> ModelVersionOut:
    mv = train_model(db)
    return ModelVersionOut(
        version=mv.version, metrics=mv.metrics, n_samples=mv.n_samples,
        feature_list=mv.feature_list, created_at=mv.created_at,
    )


@router.get(
    "/models",
    response_model=list[ModelVersionOut],
    dependencies=[Depends(require_admin)],
)
def list_models(db: Session = Depends(get_db)) -> list[ModelVersion]:
    return list(
        db.scalars(select(ModelVersion).order_by(ModelVersion.created_at.desc()))
    )
