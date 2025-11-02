from __future__ import annotations

from typing import Any, Dict, Literal

from src.vendor.pydantic import BaseModel, Field

from .analyst import Strategy


class Signal(BaseModel):
    schema_meta: Dict[str, Any] = Field(
        default_factory=lambda: {"name": "Signal", "version": 2}
    )
    symbol: str
    side: Literal["BUY", "SELL", "FLAT"]
    strategy: Strategy
    kelly_base: float
    safety_multiplier: float
    final_size_frac: float = Field(ge=0.0)
    p_final: float = Field(ge=0.0, le=1.0)
    uncertainty: float = Field(ge=0.0, le=1.0)
    reasoning: str

    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
    }
