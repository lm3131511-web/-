from __future__ import annotations

from typing import Any, Dict, List

from src.vendor.pydantic import BaseModel, Field


class AggregationContributor(BaseModel):
    stage: str
    provider: str
    weight: float
    reliability: float
    probability: float = Field(ge=0.0, le=1.0)


class AggregationResult(BaseModel):
    schema_meta: Dict[str, Any] = Field(
        default_factory=lambda: {"name": "AggregationResult", "version": 2}
    )
    contributors: List[AggregationContributor]
    p_final: float = Field(ge=0.0, le=1.0)
    uncertainty: float = Field(ge=0.0, le=1.0)
    tau_used: float = Field(ge=0.0)
    weights: Dict[str, float] = Field(default_factory=dict)
    reliability_scores: Dict[str, float] = Field(default_factory=dict)
    budget_spent_usd: float = Field(ge=0.0)
    budget_left_usd: float = Field(ge=0.0)
    degradation_mode: str

    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
    }
