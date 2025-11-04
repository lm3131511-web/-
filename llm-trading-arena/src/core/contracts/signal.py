from __future__ import annotations

from typing import Any, Dict

from src.vendor.pydantic import BaseModel, Field


class Signal(BaseModel):
    schema_meta: Dict[str, Any] = Field(
        default_factory=lambda: {"name": "Signal", "version": 2}
    )
    symbol: str
    side: str
    strategy: str
    kelly_base: float
    safety_multiplier: float
    final_size_frac: float
    regime: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}
