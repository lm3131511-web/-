from __future__ import annotations

from src.core.contracts import Signal
from src.exec.planner import ExecutionPlanner


def make_signal(z: float) -> Signal:
    return Signal(
        symbol="BTCUSDT",
        side="BUY" if z >= 0 else "SELL",
        strength=0.5,
        z_score=z,
        p_final=0.5,
        uncertainty=0.2,
        reasoning="test",
    )


def test_execution_planner_switches_strategy() -> None:
    planner = ExecutionPlanner(
        {
            "ttl_sec_range": [30, 120],
            "price_bands_atr_mult": 2.0,
            "minimal_notional_usd": 10,
            "low_top_depth_usd": 1_000_000,
            "strategies": ["POST_ONLY", "IOC"],
            "strategy_thresholds": {"strong_signal_z": 1.0},
            "post_only_queue_penalty_bps": 0.5,
        }
    )
    plan = planner.plan(make_signal(0.5), adv_fraction=0.1)
    assert plan.legs[0].strategy == "POST_ONLY"
    strong_plan = planner.plan(make_signal(1.2), adv_fraction=0.1)
    assert strong_plan.legs[0].strategy == "IOC"
