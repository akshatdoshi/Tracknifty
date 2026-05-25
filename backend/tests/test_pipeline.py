import datetime as dt

import pandas as pd

from app.pipeline.ingestion import _normalise_columns
from app.pipeline.validation import detect_gaps, validate_transactions


def test_validation_accepts_clean_rows_and_normalises_aliases():
    raw = pd.DataFrame(
        {
            "Symbol": ["infy.ns", "TCS.NS"],
            "Date": ["2024-01-02", "02/01/2024"],
            "Type": ["BUY", "b"],
            "Qty": [10, 5],
            "Rate": ["1,500.50", 3600],
        }
    )
    result = validate_transactions(_normalise_columns(raw))
    assert result.rows_valid == 2
    assert result.rows_rejected == 0
    assert set(result.clean["ticker"]) == {"INFY.NS", "TCS.NS"}
    assert set(result.clean["side"]) == {"BUY"}


def test_validation_rejects_bad_rows():
    raw = pd.DataFrame(
        {
            "ticker": ["INFY.NS", "", "TCS.NS"],
            "trade_date": ["2024-01-02", "2024-01-03", "not-a-date"],
            "side": ["BUY", "HOLD", "SELL"],
            "quantity": [10, -5, 5],
            "price": [1500, 100, 0],
        }
    )
    result = validate_transactions(raw)
    assert result.rows_valid == 1
    assert result.rows_rejected == 2


def test_missing_columns_quarantines_file():
    raw = pd.DataFrame({"ticker": ["INFY.NS"], "price": [100]})
    result = validate_transactions(raw)
    assert result.quarantined is True


def test_detect_gaps_flags_missing_business_day():
    dates = [dt.date(2024, 1, 1), dt.date(2024, 1, 2), dt.date(2024, 1, 4)]
    gaps = detect_gaps(dates)
    assert dt.date(2024, 1, 3) in gaps
