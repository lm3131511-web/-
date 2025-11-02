from __future__ import annotations

from typing import Any, Dict, Optional

from src.vendor.pydantic import BaseModel, Field


class RiskGateApproval(BaseModel):
    schema_meta: Dict[str, Any] = Field(
        default_factory=lambda: {"name": "RiskGateApproval", "version": 1}
    )
    approved: bool
    reason: Optional[str] = None
    limit_check: Dict[str, Any] = Field(default_factory=dict)
    cooldown_active: bool = False
    circuit_breaker_tripped: bool = False
    pnl_breaker_tripped: bool = False

    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
    }
