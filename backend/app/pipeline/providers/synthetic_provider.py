"""Deterministic synthetic price generator.

Prices come from a single shared market factor plus per-symbol beta, alpha and
idiosyncratic noise. Because every symbol reacts to the *same* daily market
return, the resulting series have genuine, learnable structure — real betas,
real alpha vs benchmark, real sector co-movement — which is exactly what the
feature engineering and the model need. Everything is seeded, so a given symbol
always produces the same path: reproducible across runs and machines.
"""

from __future__ import annotations

import datetime as dt
import hashlib
from functools import lru_cache

import numpy as np
import pandas as pd

from app.pipeline.providers.base import Bar, PriceProvider

INCEPTION = dt.date(2018, 1, 1)  # fixed so prices are path-consistent across calls


def _seed(text: str) -> int:
    return int(hashlib.sha256(text.encode()).hexdigest(), 16) % (2**32)


@lru_cache(maxsize=8)
def _market_log_returns(end_ordinal: int) -> dict[int, float]:
    """Shared daily market log-returns from INCEPTION..end (memoised by end)."""
    end = dt.date.fromordinal(end_ordinal)
    days = pd.bdate_range(INCEPTION, end)
    out: dict[int, float] = {}
    for ts in days:
        rng = np.random.default_rng(ts.toordinal())
        out[ts.toordinal()] = float(rng.normal(0.0004, 0.011))  # ~10% annual drift
    return out


class SyntheticProvider(PriceProvider):
    name = "synthetic"

    def _params(self, symbol: str) -> tuple[float, float, float, float]:
        if symbol.startswith("^"):  # benchmark index: pure market factor
            rng = np.random.default_rng(_seed(symbol))
            return 1.0, 0.0, 0.002, float(rng.uniform(8000, 22000))
        rng = np.random.default_rng(_seed(symbol))
        beta = float(rng.uniform(0.6, 1.4))
        # A wider, persistent alpha with lower idiosyncratic noise makes forward
        # relative returns partly predictable from momentum/alpha features — so
        # the model can learn real structure rather than fit pure noise.
        alpha_daily = float(rng.normal(0.0, 0.0015))
        idio_vol = float(rng.uniform(0.004, 0.012))
        base_price = float(rng.uniform(80, 2500))
        return beta, alpha_daily, idio_vol, base_price

    def get_history(self, symbol: str, start: dt.date, end: dt.date) -> list[Bar]:
        beta, alpha_daily, idio_vol, base_price = self._params(symbol)
        market = _market_log_returns(end.toordinal())
        days = pd.bdate_range(INCEPTION, end)
        sym_seed = _seed(symbol)

        price = base_price
        bars: list[Bar] = []
        for ts in days:
            d = ts.date()
            mret = market.get(ts.toordinal(), 0.0)
            rng = np.random.default_rng((sym_seed * 1_000_003 + ts.toordinal()) % (2**32))
            idio = float(rng.normal(0.0, idio_vol))
            log_ret = beta * mret + alpha_daily + idio
            prev = price
            price = prev * float(np.exp(log_ret))
            if d < start or d > end:
                continue
            high = max(prev, price) * (1 + abs(idio) * 0.5)
            low = min(prev, price) * (1 - abs(idio) * 0.5)
            volume = float(rng.integers(50_000, 5_000_000))
            bars.append(
                Bar(date=d, open=round(prev, 2), high=round(high, 2),
                    low=round(low, 2), close=round(price, 2), volume=volume)
            )
        return bars
