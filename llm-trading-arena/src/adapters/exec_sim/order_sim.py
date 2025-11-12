from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple

from ...core.contracts import ExecutionPlan
from ...utils.time import now_utc_iso
from .fills import SimulatedFill, create_fill
from .slippage import SlippageResult, simulate_slippage


def _slice_pattern(strategy: str, rng: random.Random) -> List[float]:
    strategy = strategy.upper()
    if strategy == "POST_ONLY":
        base = [1.0]
    elif strategy == "IOC":
        base = [rng.uniform(0.4, 0.9)]
    elif strategy == "POV":
        base = [0.25, 0.25, 0.5]
    elif strategy == "TWAP":
        base = [1 / 3, 1 / 3, 1 / 3]
    else:
        base = [1.0]
    return base


def _apply_ttl(ttl_seconds: int, pattern: List[float]) -> List[float]:
    if ttl_seconds <= 0:
        return pattern
    # longer TTL allows more slices to complete; shorter TTL reduces later slices
    decay = min(1.0, max(0.1, ttl_seconds / 120))
    adjusted: List[float] = []
    carry = 0.0
    for fraction in pattern:
        scaled = fraction * decay
        adjusted.append(scaled)
        carry += fraction - scaled
    if adjusted:
        adjusted[0] += carry  # push leftovers into the first slice
    return adjusted


def simulate_order_execution(
    plan: ExecutionPlan,
    snapshot: Dict[str, float],
    economics: Dict[str, Any],
    *,
    decision_id: str,
    rng: Optional[random.Random] = None,
) -> Tuple[List[SimulatedFill], Dict[str, Any]]:
    if rng is None:
        rng = random.Random()

    if plan.infeasible or not plan.legs:
        return [], {
            "decision_id": decision_id,
            "filled_qty": 0.0,
            "avg_price": None,
            "partial": False,
            "simulated": True,
            "timestamp": now_utc_iso(),
        }

    fills: List[SimulatedFill] = []
    total_qty = 0.0
    total_notional = 0.0
    planned_qty = sum(float(leg.quantity) for leg in plan.legs)

    mid_price = float(snapshot.get("mid_price") or snapshot.get("last_price") or 0.0)
    spread_bps = float(snapshot.get("spread_bps", 0.0))
    volatility = float(snapshot.get("volatility", snapshot.get("micro_volatility_q", 0.01)))
    depth_usd = float(snapshot.get("top_depth_usd", 1_000_000.0))

    for leg in plan.legs:
        pattern = _slice_pattern(leg.strategy, rng)
        pattern = _apply_ttl(int(getattr(leg, "ttl_seconds", 0) or 0), pattern)
        remaining_qty = float(leg.quantity)
        side = getattr(leg, "side", "BUY")
        base_price = float(getattr(leg, "price", mid_price) or mid_price)
        for fraction in pattern:
            qty = max(0.0, remaining_qty * fraction)
            if qty <= 0:
                continue
            notional = qty * base_price
            slip: SlippageResult = simulate_slippage(
                side=side,
                mid_price=mid_price or base_price,
                notional=notional,
                spread_bps=spread_bps,
                volatility=volatility,
                depth_usd=depth_usd,
                economics=economics,
                rng=rng,
            )
            executed_price = slip.executed_price
            fill = create_fill(
                decision_id=decision_id,
                asset=leg.symbol,
                price=executed_price,
                qty=qty,
                slippage_bps=slip.slippage_bps,
            )
            fills.append(fill)
            total_qty += qty
            total_notional += qty * executed_price
            remaining_qty -= qty

    avg_price = total_notional / total_qty if total_qty else None
    partial = total_qty < planned_qty - 1e-9
    summary = {
        "decision_id": decision_id,
        "filled_qty": total_qty,
        "avg_price": avg_price,
        "partial": partial,
        "simulated": True,
        "timestamp": now_utc_iso(),
    }
    return fills, summary
