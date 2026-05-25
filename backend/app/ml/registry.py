"""Model version registry.

Every trained model is written to the model store (local dir by default, S3 when
configured) and recorded as a ``ModelVersion`` row. Each generated signal stores
its ``model_version_id``, so any recommendation can be traced back to the exact
model and feature set that produced it.
"""

from __future__ import annotations

import datetime as dt
import logging
import os

import xgboost as xgb
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import ModelVersion

logger = logging.getLogger(__name__)


def _ensure_dir() -> str:
    os.makedirs(settings.model_store_dir, exist_ok=True)
    return settings.model_store_dir


def save_model(
    db: Session,
    booster: xgb.Booster,
    feature_list: list[str],
    classes: list[str],
    metrics: dict,
    n_samples: int,
) -> ModelVersion:
    version = "v" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = os.path.join(_ensure_dir(), f"{version}.json")
    booster.save_model(path)

    if settings.model_store == "s3" and settings.s3_bucket:
        _upload_s3(path, f"{version}.json")

    metrics = {**metrics, "classes": classes}
    mv = ModelVersion(
        version=version, artifact_path=path, feature_list=feature_list,
        metrics=metrics, n_samples=n_samples,
    )
    db.add(mv)
    db.commit()
    db.refresh(mv)
    logger.info("Saved model %s (%d samples)", version, n_samples)
    return mv


def load_latest(db: Session) -> tuple[xgb.Booster, ModelVersion] | None:
    mv = db.scalars(
        select(ModelVersion).order_by(ModelVersion.created_at.desc()).limit(1)
    ).first()
    if mv is None:
        return None
    booster = xgb.Booster()
    booster.load_model(mv.artifact_path)
    return booster, mv


def _upload_s3(local_path: str, key: str) -> None:
    try:
        import boto3

        boto3.client("s3").upload_file(
            local_path, settings.s3_bucket, f"models/{key}"
        )
        logger.info("Uploaded model to s3://%s/models/%s", settings.s3_bucket, key)
    except Exception as exc:  # pragma: no cover - optional path
        logger.warning("S3 upload failed (%s); model kept locally", exc)
