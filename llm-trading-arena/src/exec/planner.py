from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from ..core.contracts import ExecutionLeg, ExecutionPlan, Signal
from ..core.types import ExecutionStrategy, OrderSide


@dataclass(slots=True)
class ExecutionConfig:
    ttl_sec_range: tuple[int, int]
    price_bands_atr_mult: float
    minimal_notional_usd: float
    low_top_depth_usd: float
    strategies: List[str]
    strategy_thresholds: Dict[str, float]
    post_only_queue_penalty_bps: float

    @classmethod
    def from_mapping(cls, data: Dict[str, float | int | List[str]]) -> "ExecutionConfig":
        return cls(
            ttl_sec_range=(int(data["ttl_sec_range"][0]), int(data["ttl_sec_range"][1])),
            price_bands_atr_mult=float(data["price_bands_atr_mult"]),
            minimal_notional_usd=float(data["minimal_notional_usd"]),
            low_top_depth_usd=float(data["low_top_depth_usd"]),
            strategies=list(data["strategies"]),
            strategy_thresholds=dict(data.get("strategy_thresholds", {})),
            post_only_queue_penalty_bps=float(data["post_only_queue_penalty_bps"]),
        )


class ExecutionPlanner:
    def __init__(self, config: Dict[str, float | int | List[str]]) -> None:
        self.config = ExecutionConfig.from_mapping(config)

    def plan(self, signal: Signal, adv_fraction: float) -> ExecutionPlan:
        strategy = ExecutionStrategy.POST_ONLY.value
        if signal.z_score >= self.config.strategy_thresholds.get("strong_signal_z", 0):
            strategy = ExecutionStrategy.IOC.value
        ttl = self.config.ttl_sec_range[0]
        leg = ExecutionLeg(
            symbol=signal.symbol,
            side=OrderSide.BUY.value if signal.side == "BUY" else OrderSide.SELL.value,
            strategy=strategy,
            quantity=adv_fraction,
            price=None,
            ttl_seconds=ttl,
        )
        return ExecutionPlan(
            legs=[leg],
            minimal_notional_usd=self.config.minimal_notional_usd,
            post_only_queue_penalty_bps=self.config.post_only_queue_penalty_bps,
            notes="auto",
        )
