"""Stage 1 — ingestion.

Parses dragged-in CSV/Excel transaction files into a normalised DataFrame
against a strict schema contract. Column-name variants are mapped to canonical
names; everything else is left for the validation stage to reject.
"""

from __future__ import annotations

import io

import pandas as pd

REQUIRED_COLUMNS = ["ticker", "trade_date", "side", "quantity", "price"]
OPTIONAL_COLUMNS = ["fees", "sector"]

# Common header variants seen in broker exports -> canonical name.
COLUMN_ALIASES = {
    "symbol": "ticker",
    "stock": "ticker",
    "scrip": "ticker",
    "date": "trade_date",
    "tradedate": "trade_date",
    "transaction_date": "trade_date",
    "type": "side",
    "transaction_type": "side",
    "buy_sell": "side",
    "qty": "quantity",
    "units": "quantity",
    "shares": "quantity",
    "rate": "price",
    "avg_price": "price",
    "brokerage": "fees",
    "charges": "fees",
}


class IngestionError(Exception):
    pass


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {}
    for col in df.columns:
        key = str(col).strip().lower().replace(" ", "_")
        renamed[col] = COLUMN_ALIASES.get(key, key)
    return df.rename(columns=renamed)


def parse_upload(content: bytes, filename: str) -> pd.DataFrame:
    """Read raw bytes from an upload into a normalised DataFrame."""
    name = filename.lower()
    try:
        if name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content))
        elif name.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        else:
            raise IngestionError(f"Unsupported file type: {filename}")
    except IngestionError:
        raise
    except Exception as exc:  # malformed file
        raise IngestionError(f"Could not parse {filename}: {exc}") from exc

    return _normalise_columns(df)
