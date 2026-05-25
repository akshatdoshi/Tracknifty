"""Pydantic request/response models for the public API."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class LoginRequest(BaseModel):
    username: str
    password: str


class Driver(BaseModel):
    feature: str
    label: str
    direction: str
    contribution: float


class SignalOut(BaseModel):
    ticker: str
    sector: str
    portfolio_id: int
    portfolio_name: str
    weight_pct: float
    ret_1m_pct: float | None
    alpha_pct: float | None
    confidence: float
    signal: str
    raw_signal: str
    breach_min: bool
    breach_max: bool
    as_of_date: dt.date | None
    drivers: list[Driver] = []
    explanation: str = ""
    rule_notes: list[str] = []
    # position summary
    quantity: float
    wac: float
    current_price: float | None
    unrealised_pnl_pct: float | None
    holding_days: int
    derisked: bool
    signal_trace: list[str] = []


class PortfolioOut(BaseModel):
    id: int
    name: str
    benchmark_symbol: str
    holdings_count: int


class RuleOut(BaseModel):
    portfolio_id: int
    min_weight_pct: float
    max_weight_pct: float
    momentum_threshold_pct: float
    volatility_ceiling: float
    confidence_floor: float
    derisk_override: bool


class RuleUpdate(BaseModel):
    min_weight_pct: float | None = None
    max_weight_pct: float | None = None
    momentum_threshold_pct: float | None = None
    volatility_ceiling: float | None = None
    confidence_floor: float | None = None
    derisk_override: bool | None = None


class IngestionLogOut(BaseModel):
    id: int
    source: str
    filename: str
    status: str
    rows_total: int
    rows_ingested: int
    rows_skipped: int
    errors: list[dict]
    created_at: dt.datetime


class ModelVersionOut(BaseModel):
    version: str
    metrics: dict
    n_samples: int
    feature_list: list[str]
    created_at: dt.datetime
