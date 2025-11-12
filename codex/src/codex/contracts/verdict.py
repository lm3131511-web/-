from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List


class RiskAssessment(BaseModel):
    verdict: str
    size_multiplier: float = Field(ge=0.0, le=1.0)
    risk_tags: List[str] = Field(default_factory=list)
    short_reason: str = Field(max_length=240)
    prompt_version: str
    cache_hit: bool = False
    latency_ms: int = Field(ge=0, default=0)
    is_fallback: bool = False
    stale_correlation: bool = False

    model_config = {
        "extra": "forbid"
    }

    def capped(self, cap: float) -> "RiskAssessment":
        return self.model_copy(update={"size_multiplier": min(self.size_multiplier, cap)})
