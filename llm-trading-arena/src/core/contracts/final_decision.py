from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from src.vendor.pydantic import BaseModel, Field

from .analyst import AnalystResponse
from .aggregation import AggregationResult
from .execution import AuditInfo, ExecutionPlan
from .risk_gate import RiskGateApproval
from .signal import Signal

FinalDecisionStatus = Literal["approved", "rejected"]


class FinalDecision(BaseModel):
    schema_meta: Dict[str, Any] = Field(
        default_factory=lambda: {"name": "FinalDecision", "version": 1}
    )
    status: FinalDecisionStatus
    reason: Optional[str] = None
    analyst: AnalystResponse | None
    aggregation: AggregationResult
    signal: Signal
    risk_gate: RiskGateApproval
    execution: ExecutionPlan | None
    audit: AuditInfo

    model_config = {"extra": "allow"}
