from __future__ import annotations

from typing import Any, Dict, List

from src.vendor.pydantic import BaseModel, Field


class ExecutionLeg(BaseModel):
    schema_meta: Dict[str, Any] = Field(
        default_factory=lambda: {"name": "ExecutionLeg", "version": 1}
    )
    symbol: str
    side: str
    strategy: str
    price: float
    quantity: float
    ttl_seconds: int


class ExecutionPlan(BaseModel):
    schema_meta: Dict[str, Any] = Field(
        default_factory=lambda: {"name": "ExecutionPlan", "version": 2}
    )
    legs: List[ExecutionLeg] = Field(default_factory=list)
    idempotency_key: str
    client_order_id: str
    strategy: str
    infeasible: bool = False
    notes: Dict[str, Any] = Field(default_factory=dict)


class AuditInfo(BaseModel):
    schema_meta: Dict[str, Any] = Field(
        default_factory=lambda: {"name": "AuditInfo", "version": 2}
    )
    snapshot_id: str
    code_hash: str
    seed: int
    mode: str
    degradation_mode: str
    kill_switch_state: str

    model_config = {"extra": "allow"}
