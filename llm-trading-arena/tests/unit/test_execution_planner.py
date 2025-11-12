import pytest

from src.exec.planner import ExecutionPlanner, InfeasiblePlan
from src.core.contracts import Signal


@pytest.fixture
def planner() -> ExecutionPlanner:
    execution_cfg = {
        "enforce_exchange_filters": True,
        "ttl_sec_range": [30, 120],
        "price_bands_vol_mult": 2.0,
        "minimal_notional_usd": 10,
        "low_top_depth_usd": 100000,
        "max_spread_bps": 12,
        "strategies": ["POST_ONLY", "IOC"],
        "strategy_thresholds": {},
        "post_only_queue_penalty_bps": 0.5,
        "max_order_age_ms": 100,
        "slicing": {"enabled": False},
    }
    order_cfg = {"idempotency_prefix": "arena-"}
    return ExecutionPlanner(execution_cfg, order_cfg)


def test_planner_keeps_llm_strategy(planner: ExecutionPlanner) -> None:
    signal = Signal(
        symbol="BTCUSDT",
        side="BUY",
        strategy="POST_ONLY",
        kelly_base=0.1,
        safety_multiplier=1.0,
        final_size_frac=0.05,
        regime="stable_trend",
    )
    snapshot = {"mid_price": 100.0, "volatility": 0.01, "spread_bps": 5.0, "top_depth_usd": 200000}
    plan = planner.plan(signal=signal, market_snapshot=snapshot, price_band_hint=None, ttl_hint=None)
    assert plan.strategy == "POST_ONLY"
    assert plan.legs[0].strategy == "POST_ONLY"
    assert plan.idempotency_key
    assert plan.client_order_id.startswith("arena-")


def test_planner_rejects_unlisted_strategy(planner: ExecutionPlanner) -> None:
    signal = Signal(
        symbol="BTCUSDT",
        side="BUY",
        strategy="TWAP",
        kelly_base=0.1,
        safety_multiplier=1.0,
        final_size_frac=0.05,
        regime="chop",
    )
    snapshot = {"mid_price": 100.0, "volatility": 0.01, "spread_bps": 5.0, "top_depth_usd": 200000}
    with pytest.raises(InfeasiblePlan):
        planner.plan(signal=signal, market_snapshot=snapshot, price_band_hint=None, ttl_hint=None)
