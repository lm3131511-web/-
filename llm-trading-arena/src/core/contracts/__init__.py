from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Type

from src.vendor.pydantic import BaseModel

from .analyst import AnalystResponse
from .aggregation import AggregationResult, AggregationContributor
from .execution import ExecutionLeg, ExecutionPlan, AuditInfo
from .final_decision import FinalDecision, FinalDecisionStatus
from .risk_gate import RiskGateApproval
from .signal import Signal

__all__ = [
    "AnalystResponse",
    "AggregationResult",
    "AggregationContributor",
    "ExecutionLeg",
    "ExecutionPlan",
    "AuditInfo",
    "FinalDecision",
    "FinalDecisionStatus",
    "RiskGateApproval",
    "Signal",
    "generate_json_schemas",
]


def _iter_contracts() -> Iterable[Type[BaseModel]]:
    return (
        AnalystResponse,
        AggregationResult,
        Signal,
        RiskGateApproval,
        ExecutionPlan,
        AuditInfo,
        FinalDecision,
    )


def generate_json_schemas(target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for model in _iter_contracts():
        schema = model.model_json_schema()
        path = target_dir / f"{model.__name__}.json"
        path.write_text(json.dumps(schema, indent=2, sort_keys=True), encoding="utf-8")
