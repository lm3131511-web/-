from __future__ import annotations

from typing import Any, Dict, Optional

from src.vendor.pydantic import BaseModel, Field


class ExecutionLeg(BaseModel):
    symbol: str
    side: str
    strategy: str
    quantity: float
    price: Optional[float] = None
    ttl_seconds: Optional[int] = None
    notional_usd: Optional[float] = None


class ExecutionPlan(BaseModel):
    schema_meta: Dict[str, Any] = Field(
        default_factory=lambda: {"name": "ExecutionPlan", "version": 2}
    )
    legs: list[ExecutionLeg]
    minimal_notional_usd: float = Field(ge=0.0)
    post_only_queue_penalty_bps: float = Field(ge=0.0)
    notes: str = ""

    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
    }


class AuditInfo(BaseModel):
    schema_meta: Dict[str, Any] = Field(
        default_factory=lambda: {"name": "AuditInfo", "version": 2}
    )
    idempotency_key: str
    ts_utc: str
    snapshot_id: str
    mode: str
    code_hash: str
    seed: int
    kill_switch_state: str
    degradation_mode: str

    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
    }
