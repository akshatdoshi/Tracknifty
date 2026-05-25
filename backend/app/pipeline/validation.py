"""Stage 2 — validation & cleaning.

Every uploaded file passes through here before it can touch the ledger:
schema checks, per-row type/coercion checks, and gap detection for time-series.
Rows that fail are collected with reasons; if *nothing* survives, the whole file
is quarantined. The biggest project risk (per the outline) is dirty Excel/CSV,
so this layer is intentionally strict and fully logged.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import pandas as pd

from app.pipeline.ingestion import REQUIRED_COLUMNS

VALID_SIDES = {"BUY", "SELL"}


@dataclass
class ValidationResult:
    clean: pd.DataFrame
    errors: list[dict] = field(default_factory=list)
    rows_total: int = 0

    @property
    def rows_valid(self) -> int:
        return len(self.clean)

    @property
    def rows_rejected(self) -> int:
        return len(self.errors)

    @property
    def quarantined(self) -> bool:
        # Nothing usable came out of the file.
        return self.rows_total > 0 and self.rows_valid == 0


def validate_transactions(df: pd.DataFrame) -> ValidationResult:
    rows_total = len(df)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        return ValidationResult(
            clean=pd.DataFrame(),
            errors=[{"row": None, "reason": f"missing columns: {missing}"}],
            rows_total=rows_total,
        )

    clean_rows: list[dict] = []
    errors: list[dict] = []

    for idx, row in df.iterrows():
        reasons: list[str] = []

        ticker = str(row.get("ticker", "")).strip().upper()
        if not ticker or ticker in {"NAN", "NONE"}:
            reasons.append("empty ticker")

        trade_date = _coerce_date(row.get("trade_date"))
        if trade_date is None:
            reasons.append("invalid trade_date")

        side = str(row.get("side", "")).strip().upper()
        side = {"B": "BUY", "S": "SELL"}.get(side, side)
        if side not in VALID_SIDES:
            reasons.append(f"invalid side '{row.get('side')}'")

        quantity = _coerce_float(row.get("quantity"))
        if quantity is None or quantity <= 0:
            reasons.append("invalid quantity")

        price = _coerce_float(row.get("price"))
        if price is None or price <= 0:
            reasons.append("invalid price")

        if reasons:
            errors.append({"row": int(idx), "reason": "; ".join(reasons)})
            continue

        clean_rows.append(
            {
                "ticker": ticker,
                "trade_date": trade_date,
                "side": side,
                "quantity": quantity,
                "price": price,
                "fees": _coerce_float(row.get("fees")) or 0.0,
                "sector": str(row.get("sector", "")).strip() or None,
            }
        )

    return ValidationResult(
        clean=pd.DataFrame(clean_rows), errors=errors, rows_total=rows_total
    )


def detect_gaps(dates: list[dt.date]) -> list[dt.date]:
    """Return business days missing from an otherwise-continuous series."""
    if len(dates) < 2:
        return []
    full = pd.bdate_range(min(dates), max(dates)).date
    present = set(dates)
    return [d for d in full if d not in present]


def _coerce_date(value) -> dt.date | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        ts = pd.to_datetime(value, dayfirst=False, errors="coerce")
        if pd.isna(ts):
            ts = pd.to_datetime(value, dayfirst=True, errors="coerce")
        return None if pd.isna(ts) else ts.date()
    except Exception:
        return None


def _coerce_float(value) -> float | None:
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        return float(str(value).replace(",", ""))
    except (ValueError, TypeError):
        return None
