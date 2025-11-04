from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from src.vendor.pydantic import BaseModel, Field

Direction = Literal["BUY", "SELL", "FLAT"]
Strategy = Literal["POST_ONLY", "IOC", "POV", "TWAP"]


class PriceBandHint(BaseModel):
    schema_meta: Dict[str, Any] = Field(
        default_factory=lambda: {"name": "PriceBandHint", "version": 1}
    )
    width_bps: float = Field(ge=0.0)


class AnalystLLMOutput(BaseModel):
    direction: Direction
    strategy: Strategy
    confidence: float = Field(ge=0.0, le=1.0)
    urgency: float = Field(ge=0.0, le=1.0)
    size_hint_frac: float = Field(ge=0.0)
    ttl_hint_sec: int | None = Field(default=None, ge=0)
    price_band_bps: float | None = Field(default=None, ge=0.0)
    uncertainty_hints: List[str] = Field(default_factory=list)
    requested_features: List[str] = Field(default_factory=list)
    reliability: float = Field(default=0.5, ge=0.0, le=1.0)
    reasoning: Optional[str] = None

    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
    }


class AnalystResponse(BaseModel):
    schema_meta: Dict[str, Any] = Field(
        default_factory=lambda: {"name": "AnalystResponse", "version": 3}
    )
    stage: str
    provider: str
    prompt_version: str = "v1"
    prompt_hash: str = Field(default="", min_length=0)
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    latency_ms: float = Field(ge=0.0)
    direction: Direction
    strategy: Strategy
    confidence: float = Field(ge=0.0, le=1.0)
    urgency: float = Field(ge=0.0, le=1.0)
    size_hint_frac: float = Field(ge=0.0)
    ttl_hint_sec: int | None = Field(default=None, ge=0)
    price_band_hint: PriceBandHint | None = None
    uncertainty_hints: List[str] = Field(default_factory=list)
    requested_features: List[str] = Field(default_factory=list)
    reliability: float = Field(ge=0.0, le=1.0)
    reasoning: Optional[str] = None

    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
    }


def analyst_response_json_schema() -> Dict[str, Any]:
    """Expose the strict JSON schema shared with LLM providers."""

    return AnalystLLMOutput.model_json_schema()


__all__ = [
    "AnalystResponse",
    "PriceBandHint",
    "AnalystLLMOutput",
    "analyst_response_json_schema",
]
