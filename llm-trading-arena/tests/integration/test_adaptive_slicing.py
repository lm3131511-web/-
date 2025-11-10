import random

from src.adapters.exec_sim import simulate_order_execution
from src.core.contracts import ExecutionLeg, ExecutionPlan


def test_pov_strategy_slices_orders() -> None:
    plan = ExecutionPlan(
        legs=[
            ExecutionLeg(
                symbol="ETHUSDT",
                side="BUY",
                strategy="POV",
                price=1800.0,
                quantity=2.0,
                ttl_seconds=90,
            )
        ],
        idempotency_key="pov",
        client_order_id="client",
        strategy="POV",
    )
    economics = {
        "stress_slippage_prob": 0.3,
        "normal": {"k_vol_bps": 0.35, "sigma": 0.6},
        "stress": {"k_vol_bps": 0.75, "sigma": 1.2},
    }
    snapshot = {
        "mid_price": 1800.0,
        "spread_bps": 4.0,
        "volatility": 0.015,
        "top_depth_usd": 2_000_000.0,
    }
    fills, summary = simulate_order_execution(
        plan,
        snapshot,
        economics,
        decision_id="pov",
        rng=random.Random(1),
    )
    assert len(fills) >= 3
    assert summary["filled_qty"] > 0
