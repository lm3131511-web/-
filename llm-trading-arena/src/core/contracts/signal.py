from __future__ import annotations

from typing import Any, Dict

from src.vendor.pydantic import BaseModel, Field


class Signal(BaseModel):
    schema_meta: Dict[str, Any] = Field(
        default_factory=lambda: {"name": "Signal", "version": 1}
    )
    symbol: str
    side: str
    strength: float
    z_score: float
    p_final: float = Field(ge=0.0, le=1.0)
    uncertainty: float = Field(ge=0.0, le=1.0)
    reasoning: str

    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
    }
