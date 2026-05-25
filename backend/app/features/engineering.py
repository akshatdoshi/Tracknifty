"""Feature engineering — the four feature groups from the solution outline.

Each call produces, for one stock as of one date:

* ``features``: the numeric vector fed to the model (stable, ordered).
* ``context``:  human-facing values (weight %, 3M alpha %, volatility ratio,
  de-risk flag) the rules engine and dashboard read directly.

Position features need portfolio context; when scoring historical training
dates that context is absent, so those features fall back to ``NaN`` — which
XGBoost handles natively.
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

# Canonical, ordered feature names. The model and SHAP both rely on this order.
FEATURE_NAMES = [
    # Position
    "pos_weight", "pos_holding_days", "pos_unrealised_pnl_pct", "pos_derisked",
    # Momentum
    "mom_1w", "mom_1m", "mom_3m", "mom_6m", "mom_1y",
    # Relative performance
    "rel_alpha_3m", "rel_sector_rank", "rel_outperf_ratio",
    # Risk
    "risk_vol_30d", "risk_beta", "risk_vol_ratio",
]

# Friendly labels used in SHAP driver explanations.
FEATURE_LABELS = {
    "pos_weight": "Portfolio weight",
    "pos_holding_days": "Holding period",
    "pos_unrealised_pnl_pct": "Unrealised P&L",
    "pos_derisked": "Prior de-risking",
    "mom_1w": "1-week momentum",
    "mom_1m": "1-month momentum",
    "mom_3m": "3-month momentum",
    "mom_6m": "6-month momentum",
    "mom_1y": "1-year momentum",
    "rel_alpha_3m": "3-month alpha vs benchmark",
    "rel_sector_rank": "Sector rank vs peers",
    "rel_outperf_ratio": "Benchmark outperformance ratio",
    "risk_vol_30d": "30-day volatility",
    "risk_beta": "Beta vs Nifty 50",
    "risk_vol_ratio": "Volatility vs market",
}

WINDOWS = {"mom_1w": 5, "mom_1m": 21, "mom_3m": 63, "mom_6m": 126, "mom_1y": 252}


@dataclass
class PositionContext:
    weight_pct: float
    holding_days: int
    unrealised_pnl_pct: float
    derisked: bool


@dataclass
class FeatureBundle:
    features: dict[str, float]
    context: dict[str, float]

    def vector(self) -> list[float]:
        return [self.features.get(name, float("nan")) for name in FEATURE_NAMES]


def _slice(series: pd.Series, as_of: dt.date) -> pd.Series:
    return series[series.index <= as_of]


def _window_return(closes: np.ndarray, window: int) -> float:
    if len(closes) <= window:
        return float("nan")
    base = closes[-1 - window]
    return float(closes[-1] / base - 1.0) if base else float("nan")


def build_feature_row(
    ticker_prices: pd.Series,
    benchmark_prices: pd.Series,
    peer_prices: dict[str, pd.Series],
    as_of: dt.date,
    position: PositionContext | None = None,
) -> FeatureBundle:
    stock = _slice(ticker_prices, as_of)
    bench = _slice(benchmark_prices, as_of)
    features: dict[str, float] = {}

    # --- Position -------------------------------------------------------
    if position is not None:
        features["pos_weight"] = position.weight_pct
        features["pos_holding_days"] = float(position.holding_days)
        features["pos_unrealised_pnl_pct"] = position.unrealised_pnl_pct
        features["pos_derisked"] = 1.0 if position.derisked else 0.0
    else:
        features["pos_weight"] = float("nan")
        features["pos_holding_days"] = float("nan")
        features["pos_unrealised_pnl_pct"] = float("nan")
        features["pos_derisked"] = float("nan")

    closes = stock.to_numpy()

    # --- Momentum -------------------------------------------------------
    for name, window in WINDOWS.items():
        features[name] = _window_return(closes, window)

    # --- Relative performance ------------------------------------------
    stock_3m = features["mom_3m"]
    bench_3m = _window_return(bench.to_numpy(), WINDOWS["mom_3m"])
    features["rel_alpha_3m"] = (
        stock_3m - bench_3m
        if not (math.isnan(stock_3m) or math.isnan(bench_3m))
        else float("nan")
    )

    peer_3m_returns = []
    for series in peer_prices.values():
        peer_3m_returns.append(_window_return(_slice(series, as_of).to_numpy(), WINDOWS["mom_3m"]))
    peer_3m_returns = [r for r in peer_3m_returns if not math.isnan(r)]
    if peer_3m_returns and not math.isnan(stock_3m):
        rank = sum(1 for r in peer_3m_returns if stock_3m > r) / len(peer_3m_returns)
        features["rel_sector_rank"] = float(rank)
    else:
        features["rel_sector_rank"] = float("nan")

    features["rel_outperf_ratio"] = _outperformance_ratio(stock, bench, lookback=63)

    # --- Risk -----------------------------------------------------------
    stock_ret = stock.pct_change().dropna()
    bench_ret = bench.pct_change().dropna()
    vol_30 = (
        float(stock_ret.tail(30).std() * math.sqrt(252))
        if len(stock_ret) >= 5 else float("nan")
    )
    features["risk_vol_30d"] = vol_30

    beta, vol_ratio = _beta_and_vol_ratio(stock_ret, bench_ret, window=120)
    features["risk_beta"] = beta
    features["risk_vol_ratio"] = vol_ratio

    context = {
        "weight_pct": features["pos_weight"],
        "momentum_vs_benchmark_pct": (features["rel_alpha_3m"] * 100.0)
        if not math.isnan(features["rel_alpha_3m"]) else float("nan"),
        "vol_ratio": vol_ratio,
        "derisked": features["pos_derisked"],
        "ret_1m_pct": (features["mom_1m"] * 100.0)
        if not math.isnan(features["mom_1m"]) else float("nan"),
    }
    return FeatureBundle(features=features, context=context)


def _outperformance_ratio(stock: pd.Series, bench: pd.Series, lookback: int) -> float:
    s = stock.pct_change().dropna().tail(lookback)
    b = bench.pct_change().dropna().tail(lookback)
    aligned = pd.concat([s, b], axis=1, join="inner").dropna()
    if len(aligned) < 5:
        return float("nan")
    wins = (aligned.iloc[:, 0] > aligned.iloc[:, 1]).mean()
    return float(wins)


def _beta_and_vol_ratio(
    stock_ret: pd.Series, bench_ret: pd.Series, window: int
) -> tuple[float, float]:
    aligned = pd.concat(
        [stock_ret.tail(window), bench_ret.tail(window)], axis=1, join="inner"
    ).dropna()
    if len(aligned) < 20:
        return float("nan"), float("nan")
    s, b = aligned.iloc[:, 0], aligned.iloc[:, 1]
    var_b = float(b.var())
    beta = float(np.cov(s, b)[0, 1] / var_b) if var_b > 0 else float("nan")
    vol_ratio = float(s.std() / b.std()) if b.std() > 0 else float("nan")
    return beta, vol_ratio
