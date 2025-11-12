from __future__ import annotations

from pydantic import BaseModel, Field


class DeterministicFeatures(BaseModel):
    regime: str
    rsi_14: float
    atr_pct: float = Field(ge=0)
    spread_bps: float = Field(ge=0)
    correlation_rho: float | None = None
    correlation_ts_seconds: int | None = None


class MetaContext(BaseModel):
    mode: str = "live"
    portfolio_limited: bool = False
    open_correlation_rho: float | None = None
