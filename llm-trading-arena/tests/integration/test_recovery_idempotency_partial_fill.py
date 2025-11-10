import random

from src.adapters.exec_sim import simulate_order_execution
from src.core.contracts import ExecutionLeg, ExecutionPlan


def test_simulated_partial_fill_marks_summary() -> None:
    plan = ExecutionPlan(
        legs=[
            ExecutionLeg(
                symbol="BTCUSDT",
                side="BUY",
                strategy="IOC",
                price=100.0,
                quantity=1.0,
                ttl_seconds=30,
            )
        ],
        idempotency_key="key",
        client_order_id="client",
        strategy="IOC",
    )
    economics = {
        "stress_slippage_prob": 0.0,
        "normal": {"k_vol_bps": 0.35, "sigma": 0.6},
        "stress": {"k_vol_bps": 0.75, "sigma": 1.2},
    }
    snapshot = {
        "mid_price": 100.0,
        "spread_bps": 5.0,
        "volatility": 0.02,
        "top_depth_usd": 1_000_000.0,
    }
    fills, summary = simulate_order_execution(
        plan,
        snapshot,
        economics,
        decision_id="key",
        rng=random.Random(0),
    )
    total_qty = sum(fill.qty for fill in fills)
    assert summary["partial"] is True
    assert total_qty < 1.0
    assert all(fill.decision_id == "key" for fill in fills)
