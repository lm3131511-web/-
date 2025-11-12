from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..contracts.sentiment import AggregatedSentiment


class CacheEntry(BaseModel):
    key: str
    value: Dict[str, Any]
    expires_at: float


class DecisionRecord(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    prompt_version: str
    verdict: str
    size_multiplier: float
    risk_tags: List[str]
    cache_hit: bool
    latency_ms: int
    fingerprint_hash: str
    is_fallback: bool = False
    stale_correlation: bool = False
    short_reason: Optional[str] = None

    model_config = {
        "json_encoders": {datetime: lambda dt: dt.replace(tzinfo=None).isoformat(timespec="seconds") + "Z"}
    }


class NewsIngestRecord(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    aggregated: AggregatedSentiment
    provider_counts: Dict[str, int]
    items: List[Dict[str, Any]]

    model_config = {
        "json_encoders": {datetime: lambda dt: dt.replace(tzinfo=None).isoformat(timespec="seconds") + "Z"}
    }
