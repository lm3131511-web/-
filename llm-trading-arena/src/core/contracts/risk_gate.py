from __future__ import annotations

from typing import Any, Dict

from src.vendor.pydantic import BaseModel, Field


class RiskGateApproval(BaseModel):
    schema_meta: Dict[str, Any] = Field(
        default_factory=lambda: {"name": "RiskGateApproval", "version": 2}
    )
    approved: bool
    reason: str
    limit_check: Dict[str, Any]
    cooldown_active: bool
    circuit_breaker_tripped: bool
    pnl_breaker_tripped: bool
    infeasible: bool = False

    model_config = {"extra": "allow"}
