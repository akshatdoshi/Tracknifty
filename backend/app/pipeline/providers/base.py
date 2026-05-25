"""Price provider interface.

A provider returns daily OHLCV bars for a symbol over a date range. Two
implementations exist: :class:`SyntheticProvider` (deterministic, offline) and
:class:`YFinanceProvider` (real market data). The factory picks one based on
config, with an ``auto`` mode that prefers yfinance and falls back to synthetic.
"""

from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Bar:
    date: dt.date
    open: float
    high: float
    low: float
    close: float
    volume: float


class PriceProvider(ABC):
    name: str = "base"

    @abstractmethod
    def get_history(
        self, symbol: str, start: dt.date, end: dt.date
    ) -> list[Bar]:
        """Return daily bars for ``symbol`` in ``[start, end]`` (business days)."""

    def get_latest(self, symbol: str) -> Bar | None:
        today = dt.date.today()
        bars = self.get_history(symbol, today - dt.timedelta(days=10), today)
        return bars[-1] if bars else None
