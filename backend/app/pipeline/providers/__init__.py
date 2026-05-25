"""Price providers: a pluggable source of daily OHLCV bars."""

from app.pipeline.providers.factory import get_price_provider

__all__ = ["get_price_provider"]
