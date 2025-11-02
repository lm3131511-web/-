from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from ..core.contracts import ExecutionLeg, ExecutionPlan, Signal
from ..core.types import ExecutionStrategy, OrderSide


@dataclass(slots=True)
class ExecutionConfig:
    enforce_exchange_filters: bool
    ttl_sec_range: tuple[int, int]
    price_bands_vol_mult: float
    minimal_notional_usd: float
    low_top_depth_usd: float
    strategies: List[str]
    strategy_thresholds: Dict[str, float]
    post_only_queue_penalty_bps: float

    @classmethod
    def from_mapping(cls, data: Dict[str, object]) -> "ExecutionConfig":
        return cls(
            enforce_exchange_filters=bool(data.get("enforce_exchange_filters", True)),
            ttl_sec_range=(int(data["ttl_sec_range"][0]), int(data["ttl_sec_range"][1])),
            price_bands_vol_mult=float(data["price_bands_vol_mult"]),
            minimal_notional_usd=float(data["minimal_notional_usd"]),
            low_top_depth_usd=float(data["low_top_depth_usd"]),
            strategies=list(data["strategies"]),
            strategy_thresholds=dict(data.get("strategy_thresholds", {})),
            post_only_queue_penalty_bps=float(data["post_only_queue_penalty_bps"]),
        )


class InfeasiblePlan(RuntimeError):
    pass


class ExecutionPlanner:
    def __init__(self, config: Dict[str, object]) -> None:
        self.config = ExecutionConfig.from_mapping(config)

    def plan(
        self,
        *,
        signal: Signal,
        market_snapshot: Dict[str, float],
        price_band_bps: float | None,
        ttl_hint: int | None,
        notional_usd: float,
    ) -> ExecutionPlan:
        if signal.strategy not in self.config.strategies:
            raise InfeasiblePlan(f"strategy {signal.strategy} not enabled")

        ttl = ttl_hint or self.config.ttl_sec_range[0]
        ttl = max(self.config.ttl_sec_range[0], min(self.config.ttl_sec_range[1], ttl))
        volatility = market_snapshot.get("volatility", 0.01)
        mid_price = market_snapshot.get("mid", 0.0)
        if mid_price <= 0:
            raise InfeasiblePlan("missing mid price")
        band_bps = price_band_bps or (self.config.price_bands_vol_mult * volatility * 10_000)
        band_multiplier = band_bps / 10_000
        price = mid_price * (1 + band_multiplier if signal.side == "BUY" else 1 - band_multiplier)
        leg = ExecutionLeg(
            symbol=signal.symbol,
            side=signal.side,
            strategy=signal.strategy,
            quantity=signal.final_size_frac,
            price=round(price, 8),
            ttl_seconds=ttl,
            notional_usd=notional_usd,
        )
        return ExecutionPlan(
            legs=[leg],
            minimal_notional_usd=self.config.minimal_notional_usd,
            post_only_queue_penalty_bps=self.config.post_only_queue_penalty_bps,
            notes="llm-driven",
        )
