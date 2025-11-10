import pytest

from src.core.contracts import Signal
from src.exec.planner import ExecutionPlanner, InfeasiblePlan


@pytest.fixture
def planner() -> ExecutionPlanner:
    execution_cfg = {
        "enforce_exchange_filters": True,
        "ttl_sec_range": [30, 120],
        "price_bands_vol_mult": 2.0,
        "minimal_notional_usd": 10,
        "low_top_depth_usd": 800_000,
        "max_spread_bps": 12,
        "strategies": ["POST_ONLY", "IOC", "POV", "TWAP"],
        "strategy_thresholds": {},
        "post_only_queue_penalty_bps": 0.5,
        "max_order_age_ms": 100,
        "slicing": {"enabled": False},
    }
    order_cfg = {"idempotency_prefix": "arena-"}
    return ExecutionPlanner(execution_cfg=execution_cfg, order_cfg=order_cfg)


def _base_signal(strategy: str = "POST_ONLY") -> Signal:
    return Signal(
        symbol="BTCUSDT",
        side="BUY",
        strategy=strategy,
        kelly_base=0.1,
        safety_multiplier=1.0,
        final_size_frac=0.1,
        regime="stable",
    )


def test_spread_guard_marks_infeasible(planner: ExecutionPlanner) -> None:
    snapshot = {
        "mid_price": 100.0,
        "spread_bps": 20.0,
        "volatility": 0.01,
        "top_depth_usd": 1_000_000.0,
    }
    with pytest.raises(InfeasiblePlan):
        planner.plan(signal=_base_signal(), market_snapshot=snapshot, price_band_hint=None, ttl_hint=None)


def test_depth_guard_marks_infeasible(planner: ExecutionPlanner) -> None:
    snapshot = {
        "mid_price": 100.0,
        "spread_bps": 5.0,
        "volatility": 0.01,
        "top_depth_usd": 100_000.0,
    }
    with pytest.raises(InfeasiblePlan):
        planner.plan(signal=_base_signal(), market_snapshot=snapshot, price_band_hint=None, ttl_hint=None)
