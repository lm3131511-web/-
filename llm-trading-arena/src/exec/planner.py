from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from ..core.contracts import ExecutionLeg, ExecutionPlan, Signal
from ..utils.ids import client_order_id, decision_idempotency_key


@dataclass
class ExecutionConfig:
    enforce_exchange_filters: bool
    ttl_sec_range: tuple[int, int]
    price_bands_vol_mult: float
    minimal_notional_usd: float
    low_top_depth_usd: float
    max_spread_bps: float
    strategies: list[str]
    strategy_thresholds: Dict[str, float]
    post_only_queue_penalty_bps: float
    max_order_age_ms: int
    slicing_enabled: bool

    @classmethod
    def from_mapping(cls, data: Dict[str, object]) -> "ExecutionConfig":
        ttl_range = data.get("ttl_sec_range", [30, 120])
        return cls(
            enforce_exchange_filters=bool(data.get("enforce_exchange_filters", True)),
            ttl_sec_range=(int(ttl_range[0]), int(ttl_range[1])),
            price_bands_vol_mult=float(data.get("price_bands_vol_mult", 2.0)),
            minimal_notional_usd=float(data.get("minimal_notional_usd", 10)),
            low_top_depth_usd=float(data.get("low_top_depth_usd", 1_000_000)),
            max_spread_bps=float(data.get("max_spread_bps", 15)),
            strategies=list(data.get("strategies", [])),
            strategy_thresholds=dict(data.get("strategy_thresholds", {})),
            post_only_queue_penalty_bps=float(data.get("post_only_queue_penalty_bps", 0.5)),
            max_order_age_ms=int(data.get("max_order_age_ms", 100)),
            slicing_enabled=bool(data.get("slicing", {}).get("enabled", False)),
        )


class InfeasiblePlan(RuntimeError):
    """Raised when the execution plan cannot honour the LLM strategy."""


class ExecutionPlanner:
    def __init__(self, execution_cfg: Dict[str, object], order_cfg: Dict[str, object]) -> None:
        self.config = ExecutionConfig.from_mapping(execution_cfg)
        self.id_prefix = str(order_cfg.get("idempotency_prefix", "arena-"))

    def plan(
        self,
        *,
        signal: Signal,
        market_snapshot: Dict[str, float],
        price_band_hint: float | None,
        ttl_hint: int | None,
    ) -> ExecutionPlan:
        if signal.strategy not in self.config.strategies:
            raise InfeasiblePlan(f"strategy {signal.strategy} not enabled")
        spread_bps = market_snapshot.get("spread_bps", 0.0)
        top_depth = market_snapshot.get("top_depth_usd", float("inf"))
        if spread_bps > self.config.max_spread_bps:
            raise InfeasiblePlan("spread exceeds execution guard")
        if top_depth < self.config.low_top_depth_usd:
            raise InfeasiblePlan("top depth too shallow")
        mid = market_snapshot.get("mid_price", 0.0)
        if mid <= 0:
            raise InfeasiblePlan("missing mid price")
        volatility = market_snapshot.get("volatility", 0.01)
        band_bps = price_band_hint or (self.config.price_bands_vol_mult * volatility * 10_000)
        adjustment = band_bps / 10_000
        if signal.side == "BUY":
            price = mid * (1 + adjustment)
        else:
            price = mid * (1 - adjustment)
        ttl = ttl_hint or self.config.ttl_sec_range[0]
        ttl = max(self.config.ttl_sec_range[0], min(self.config.ttl_sec_range[1], ttl))
        quantity = max(0.0, signal.final_size_frac)
        if quantity <= 0:
            raise InfeasiblePlan("non-positive quantity")
        leg = ExecutionLeg(
            symbol=signal.symbol,
            side=signal.side,
            strategy=signal.strategy,
            price=price,
            quantity=quantity,
            ttl_seconds=ttl,
        )
        idem_key = decision_idempotency_key(
            prefix=self.id_prefix,
            symbol=signal.symbol,
            side=signal.side,
            strategy=signal.strategy,
            ttl=ttl,
            price=price,
            size_frac=signal.final_size_frac,
        )
        client_id = client_order_id(
            prefix=self.id_prefix,
            symbol=signal.symbol,
            side=signal.side,
            price=price,
            size_frac=signal.final_size_frac,
            ttl=ttl,
        )
        return ExecutionPlan(
            legs=[leg],
            idempotency_key=idem_key,
            client_order_id=client_id,
            strategy=signal.strategy,
            infeasible=False,
            notes={"price_band_bps": band_bps},
        )
