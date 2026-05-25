"""yfinance-backed price provider (production source).

This is the real market feed named in the solution outline. In a sandboxed
environment without outbound access to Yahoo Finance it will raise, which is
why the factory's ``auto`` mode falls back to the synthetic provider.
"""

from __future__ import annotations

import datetime as dt

from app.pipeline.providers.base import Bar, PriceProvider


class YFinanceProvider(PriceProvider):
    name = "yfinance"

    def get_history(self, symbol: str, start: dt.date, end: dt.date) -> list[Bar]:
        import yfinance as yf

        df = yf.download(
            symbol,
            start=start.isoformat(),
            end=(end + dt.timedelta(days=1)).isoformat(),
            progress=False,
            auto_adjust=True,
        )
        if df is None or df.empty:
            return []
        # yfinance may return a MultiIndex column frame for single tickers.
        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df.columns = df.columns.get_level_values(0)
        bars: list[Bar] = []
        for idx, row in df.iterrows():
            bars.append(
                Bar(
                    date=idx.date(),
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=float(row.get("Volume", 0) or 0),
                )
            )
        return bars
