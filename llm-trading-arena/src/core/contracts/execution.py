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


class ExecutionPlan(BaseModel):
    schema_meta: Dict[str, Any] = Field(
        default_factory=lambda: {"name": "ExecutionPlan", "version": 1}
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
        default_factory=lambda: {"name": "AuditInfo", "version": 1}
    )
    idempotency_key: str
    created_at: float
    snapshot_id: str
    mode: str
    operator: str = "system"

    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
    }
