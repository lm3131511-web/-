from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.vendor.pydantic import BaseModel, Field


class AnalystResponse(BaseModel):
    schema_meta: Dict[str, Any] = Field(
        default_factory=lambda: {"name": "AnalystResponse", "version": 1}
    )
    stage: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    reasoning: Optional[str] = None
    decision_confidence: float = Field(ge=0.0, le=1.0)
    recommended_action: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    features: List[str] = Field(default_factory=list)

    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
    }
