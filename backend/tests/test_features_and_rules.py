import datetime as dt

from app.config import settings
from app.features.engineering import (
    FEATURE_NAMES,
    PositionContext,
    build_feature_row,
)
from app.ml.labels import label_for_alpha
from app.ml.score import Prediction
from app.pipeline.providers.synthetic_provider import SyntheticProvider
from app.rules.engine import apply_rules


def _series(symbol: str):
    import pandas as pd

    provider = SyntheticProvider()
    end = dt.date(2025, 1, 1)
    bars = provider.get_history(symbol, end - dt.timedelta(days=600), end)
    return pd.Series({b.date: b.close for b in bars})


def test_feature_row_has_all_features():
    stock = _series("INFY.NS")
    bench = _series("^NSEI")
    bundle = build_feature_row(
        stock, bench, {"TCS.NS": _series("TCS.NS")}, stock.index[-1],
        PositionContext(weight_pct=8.0, holding_days=200, unrealised_pnl_pct=12.0, derisked=False),
    )
    for name in FEATURE_NAMES:
        assert name in bundle.features
    assert bundle.context["weight_pct"] == 8.0


def test_label_thresholds():
    assert label_for_alpha(settings.label_buy_alpha_pct + 1) == "BUY"
    assert label_for_alpha(settings.label_sell_alpha_pct - 1) == "SELL"
    assert label_for_alpha(0.0) == "HOLD"


class _Rule:
    min_weight_pct = 10.0
    max_weight_pct = 15.0
    momentum_threshold_pct = 5.0
    volatility_ceiling = 1.5
    confidence_floor = 60.0
    derisk_override = True


def _pred(signal, conf):
    return Prediction(signal=signal, confidence=conf, class_idx=0, drivers=[], explanation="")


def test_buy_suppressed_when_overweight():
    ctx = {"weight_pct": 12.0, "momentum_vs_benchmark_pct": 10.0, "vol_ratio": 1.0, "derisked": 0.0}
    out = apply_rules(_pred("BUY", 80), ctx, _Rule())
    assert out.signal == "HOLD"
    assert any("buy ceiling" in n.lower() for n in out.notes)


def test_buy_suppressed_below_confidence_floor():
    ctx = {"weight_pct": 5.0, "momentum_vs_benchmark_pct": 10.0, "vol_ratio": 1.0, "derisked": 0.0}
    out = apply_rules(_pred("BUY", 50), ctx, _Rule())
    assert out.signal == "HOLD"


def test_buy_allowed_when_all_guardrails_pass():
    ctx = {"weight_pct": 5.0, "momentum_vs_benchmark_pct": 10.0, "vol_ratio": 1.0, "derisked": 0.0}
    out = apply_rules(_pred("BUY", 85), ctx, _Rule())
    assert out.signal == "BUY"


def test_overweight_flags_for_sell_review():
    ctx = {"weight_pct": 20.0, "momentum_vs_benchmark_pct": 1.0, "vol_ratio": 1.0, "derisked": 0.0}
    out = apply_rules(_pred("HOLD", 70), ctx, _Rule())
    assert out.breach_max is True
    assert any("max" in n.lower() for n in out.notes)
