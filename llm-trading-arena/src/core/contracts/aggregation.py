from __future__ import annotations

from typing import Any, Dict, List

from src.vendor.pydantic import BaseModel, Field


class AggregationContributor(BaseModel):
    schema_meta: Dict[str, Any] = Field(
        default_factory=lambda: {"name": "AggregationContributor", "version": 1}
    )
    stage: str
    provider: str
    weight: float
    reliability: float
    probability: float


class AggregationResult(BaseModel):
    schema_meta: Dict[str, Any] = Field(
        default_factory=lambda: {"name": "AggregationResult", "version": 2}
    )
    contributors: List[AggregationContributor]
    p_final: float
    uncertainty: float
    tau_used: float
    weights: Dict[str, float]
    reliability_scores: Dict[str, float]
    budget_spent_usd: float
    budget_left_usd: float
    degradation_mode: str
    updated_at: str

    model_config = {"extra": "forbid"}
