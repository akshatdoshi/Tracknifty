"""Central configuration.

The whole point of this module is to let the same codebase run two ways:

* **Lightweight / local** (the default): SQLite, an in-memory cache, an
  in-process APScheduler, and the deterministic synthetic price provider.
  Nothing external is required, so it runs and is verifiable anywhere.
* **Production-shaped**: Postgres + TimescaleDB, Redis, Celery and the
  yfinance price feed — selected purely through environment variables, no
  code changes.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Persistence -------------------------------------------------------
    database_url: str = f"sqlite:///{BACKEND_ROOT / 'tracknifty.db'}"

    # --- Cache (Redis when set, otherwise in-memory TTL dict) --------------
    redis_url: str | None = None
    cache_ttl_seconds: int = 900  # 15 min, matches the live-price cadence

    # --- Scheduler ---------------------------------------------------------
    scheduler: str = "apscheduler"  # "apscheduler" | "celery"
    enable_scheduler: bool = True

    # --- Price provider ----------------------------------------------------
    price_provider: str = "auto"  # "auto" | "yfinance" | "synthetic"
    price_history_years: int = 5

    # --- Model store -------------------------------------------------------
    model_store: str = "local"  # "local" | "s3"
    model_store_dir: str = str(BACKEND_ROOT / "model_store")
    s3_bucket: str | None = None

    # --- Auth --------------------------------------------------------------
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 720

    # --- Label construction (must be signed off by the investment team) ----
    label_forward_days: int = 63           # ~3 trading months
    label_buy_alpha_pct: float = 5.0       # outperform benchmark by >X%
    label_sell_alpha_pct: float = -5.0     # underperform benchmark by >Y%

    # --- Rule defaults (per-portfolio overrides live in the DB) ------------
    default_min_weight_pct: float = 10.0
    default_max_weight_pct: float = 15.0
    default_momentum_threshold_pct: float = 5.0
    default_volatility_ceiling: float = 1.5
    default_confidence_floor: float = 60.0
    default_derisk_override: bool = True
    derisk_extra_confidence: float = 15.0  # extra confidence required post de-risk

    # --- Misc --------------------------------------------------------------
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
