from __future__ import annotations

from typing import List, Optional

from src.vendor.pydantic import BaseModel, Field


class RefereeVerdict(BaseModel):
    schema_meta: dict[str, object] = Field(
        default_factory=lambda: {"name": "RefereeVerdict", "version": 1}
    )
    feasible: bool = True
    issues: List[str] = Field(default_factory=list)
    adjusted_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    model_config = {"extra": "forbid"}
