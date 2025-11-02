from __future__ import annotations

from typing import Any, Dict, List

from src.vendor.pydantic import BaseModel, Field


class AggregationContributor(BaseModel):
    stage: str
    weight: float
    p_hat: float


class AggregationResult(BaseModel):
    schema_meta: Dict[str, Any] = Field(
        default_factory=lambda: {"name": "AggregationResult", "version": 1}
    )
    contributors: List[AggregationContributor]
    p_final: float = Field(ge=0.0, le=1.0)
    uncertainty: float = Field(ge=0.0, le=1.0)
    tau: float = Field(ge=0.0)
    budget_spent_usd: float = Field(ge=0.0)

    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
    }
