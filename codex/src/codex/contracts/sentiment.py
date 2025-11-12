from __future__ import annotations

from pydantic import BaseModel, Field


class SentimentEvent(BaseModel):
    source: str
    severity: str = "none"
    sentiment: float = Field(ge=-1.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    trusted: bool = False


class AggregatedSentiment(BaseModel):
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    event_severity: str
    confidence: float = Field(ge=0.0, le=1.0)
    sources_confirmed: int = 0
