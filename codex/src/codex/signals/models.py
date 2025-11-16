from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Literal

from pydantic import BaseModel, Field

from ..contracts.sentiment import AggregatedSentiment


class SignalCandidate(BaseModel):
    instrument: str
    timeframe: str
    side: Literal["buy", "sell"]
    entry_price: float = Field(ge=0)
    stop_loss: float = Field(ge=0)
    take_profit: float = Field(ge=0)
    strategy: str
    strategy_confidence: float = Field(ge=0.0, le=1.0)
    features: dict[str, float]
    sentiment: AggregatedSentiment
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def rr_ratio(self) -> float:
        diff_tp = self.take_profit - self.entry_price
        diff_sl = self.entry_price - self.stop_loss
        if self.side == "sell":
            diff_tp = self.entry_price - self.take_profit
            diff_sl = self.stop_loss - self.entry_price
        if diff_sl == 0:
            return 0.0
        return round(diff_tp / max(diff_sl, 1e-9), 4)


class SignalExplanation(BaseModel):
    explanation: str
    confidence: float = Field(ge=0.0, le=1.0)
    key_drivers: List[str] = Field(default_factory=list)
    risk_callouts: List[str] = Field(default_factory=list)
    timeframe_alignment: Literal["scalp", "intra", "swing", "position"]
    recommended_action: Literal["publish", "defer", "drop"]
    short_summary: str


class MetaDecision(BaseModel):
    final_verdict: Literal["BLOCK", "DENY", "DOWNGRADE", "CONFIRM", "UPGRADE", "KILL_SWITCH"]
    priority: Literal["low", "normal", "high"] = "normal"
    warnings: List[str] = Field(default_factory=list)
    llm_confidence: float = Field(ge=0.0, le=1.0)
    status_note: str
    publish: bool
    annotations: List[str] = Field(default_factory=list)
    recommended_tags: List[str] = Field(default_factory=list)
    explanation: str


class FinalSignal(BaseModel):
    instrument: str
    timeframe: str
    side: Literal["buy", "sell"]
    entry_price: float
    stop_loss: float
    take_profit: float
    rr_ratio: float
    strategy_name: str
    strategy_confidence: float
    risk_verdict: str
    llm_confidence: float | None = None
    risk_tags: List[str]
    explanation: str
    created_at: datetime
    valid_until: datetime
    risk_reason: str
    status: Literal["normal", "degraded", "blocked"]
    publish: bool
    annotations: List[str] = Field(default_factory=list)

    @classmethod
    def from_components(
        cls,
        candidate: SignalCandidate,
        risk_verdict: str,
        risk_tags: List[str],
        risk_reason: str,
        meta_decision: MetaDecision,
        explanation: SignalExplanation,
        validity_minutes: int = 90,
    ) -> "FinalSignal":
        created = candidate.created_at
        valid_until = created + timedelta(minutes=validity_minutes)
        status = "blocked"
        if meta_decision.publish and meta_decision.final_verdict in {"CONFIRM", "UPGRADE"}:
            status = "normal"
        elif meta_decision.publish:
            status = "degraded"
        return cls(
            instrument=candidate.instrument,
            timeframe=candidate.timeframe,
            side=candidate.side,
            entry_price=candidate.entry_price,
            stop_loss=candidate.stop_loss,
            take_profit=candidate.take_profit,
            rr_ratio=candidate.rr_ratio,
            strategy_name=candidate.strategy,
            strategy_confidence=candidate.strategy_confidence,
            risk_verdict=risk_verdict,
            llm_confidence=meta_decision.llm_confidence,
            risk_tags=sorted(set(risk_tags + meta_decision.recommended_tags)),
            explanation=explanation.short_summary,
            created_at=created,
            valid_until=valid_until,
            risk_reason=risk_reason,
            status=status,
            publish=meta_decision.publish,
            annotations=meta_decision.annotations,
        )
