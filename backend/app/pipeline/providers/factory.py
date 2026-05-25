"""Provider selection.

``auto`` (the default) probes yfinance once with a quick request; if it fails
for any reason — no network, host not allow-listed, rate limit — it logs the
reason and transparently falls back to the synthetic provider so the system is
always runnable.
"""

from __future__ import annotations

import datetime as dt
import logging
from functools import lru_cache

from app.config import settings
from app.pipeline.providers.base import PriceProvider
from app.pipeline.providers.synthetic_provider import SyntheticProvider
from app.pipeline.providers.yfinance_provider import YFinanceProvider

logger = logging.getLogger(__name__)


def _yfinance_is_reachable() -> bool:
    try:
        provider = YFinanceProvider()
        end = dt.date.today()
        bars = provider.get_history("AAPL", end - dt.timedelta(days=7), end)
        return len(bars) > 0
    except Exception as exc:  # network blocked, package issue, etc.
        logger.warning("yfinance unavailable (%s); using synthetic prices", exc)
        return False


@lru_cache(maxsize=1)
def get_price_provider() -> PriceProvider:
    choice = settings.price_provider.lower()
    if choice == "synthetic":
        logger.info("Price provider: synthetic (configured)")
        return SyntheticProvider()
    if choice == "yfinance":
        logger.info("Price provider: yfinance (configured)")
        return YFinanceProvider()

    # auto
    if _yfinance_is_reachable():
        logger.info("Price provider: yfinance (auto-detected reachable)")
        return YFinanceProvider()
    logger.info("Price provider: synthetic (auto fallback)")
    return SyntheticProvider()
