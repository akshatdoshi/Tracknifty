"""Ingestion API — file upload + data-quality surface for the admin."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_owned_portfolio, require_admin
from app.db.base import get_db
from app.db.models import IngestionLog, Portfolio
from app.pipeline.ingestion import IngestionError, parse_upload
from app.pipeline.validation import validate_transactions
from app.pipeline.enrichment import ingest_transactions
from app.schemas import IngestionLogOut
from app.services.dashboard import invalidate

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])


@router.post("/{portfolio_id}/upload", response_model=IngestionLogOut)
async def upload_transactions(
    portfolio: Portfolio = Depends(get_owned_portfolio),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> IngestionLog:
    content = await file.read()
    try:
        df = parse_upload(content, file.filename or "upload.csv")
    except IngestionError as exc:
        log = IngestionLog(
            source="upload", filename=file.filename or "", status="QUARANTINED",
            rows_total=0, errors=[{"row": None, "reason": str(exc)}],
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    result = validate_transactions(df)
    log = ingest_transactions(db, portfolio.id, result, file.filename or "upload.csv")
    invalidate(portfolio.id)
    return log


@router.get("/logs", response_model=list[IngestionLogOut], dependencies=[Depends(require_admin)])
def ingestion_logs(db: Session = Depends(get_db), limit: int = 50) -> list[IngestionLog]:
    return list(
        db.scalars(
            select(IngestionLog).order_by(IngestionLog.created_at.desc()).limit(limit)
        )
    )


@router.get("/quality", dependencies=[Depends(require_admin)])
def data_quality(db: Session = Depends(get_db)) -> dict:
    """Ingestion success rate, quarantine counts, last-updated per source."""
    total = db.scalar(select(func.count(IngestionLog.id))) or 0
    quarantined = db.scalar(
        select(func.count(IngestionLog.id)).where(IngestionLog.status == "QUARANTINED")
    ) or 0
    success = db.scalar(
        select(func.count(IngestionLog.id)).where(IngestionLog.status == "SUCCESS")
    ) or 0
    by_source = {}
    rows = db.execute(
        select(
            IngestionLog.source,
            func.max(IngestionLog.created_at),
            func.count(IngestionLog.id),
        ).group_by(IngestionLog.source)
    ).all()
    for source, last, count in rows:
        by_source[source] = {"last_updated": last, "count": count}

    return {
        "total_ingestions": total,
        "success": success,
        "quarantined": quarantined,
        "success_rate": round(success / total, 3) if total else None,
        "by_source": by_source,
    }
