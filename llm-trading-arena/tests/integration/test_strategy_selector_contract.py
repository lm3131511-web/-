import pytest

from src.core.contracts import Signal
from src.exec.planner import ExecutionPlanner, InfeasiblePlan


def _planner(strategies):
    execution_cfg = {
        "enforce_exchange_filters": True,
        "ttl_sec_range": [30, 120],
        "price_bands_vol_mult": 1.0,
        "minimal_notional_usd": 10,
        "low_top_depth_usd": 100_000,
        "max_spread_bps": 15,
        "strategies": strategies,
        "strategy_thresholds": {},
        "post_only_queue_penalty_bps": 0.5,
        "max_order_age_ms": 100,
        "slicing": {"enabled": False},
    }
    order_cfg = {"idempotency_prefix": "arena-"}
    return ExecutionPlanner(execution_cfg=execution_cfg, order_cfg=order_cfg)


def _snapshot():
    return {
        "mid_price": 100.0,
        "spread_bps": 5.0,
        "volatility": 0.01,
        "top_depth_usd": 1_000_000.0,
    }


def _signal(strategy: str) -> Signal:
    return Signal(
        symbol="BTCUSDT",
        side="BUY",
        strategy=strategy,
        kelly_base=0.2,
        safety_multiplier=1.0,
        final_size_frac=0.2,
        regime="stable",
    )


def test_planner_preserves_llm_strategy() -> None:
    planner = _planner(["IOC", "POST_ONLY"])
    plan = planner.plan(signal=_signal("IOC"), market_snapshot=_snapshot(), price_band_hint=None, ttl_hint=None)
    assert plan.strategy == "IOC"
    assert plan.legs[0].strategy == "IOC"


def test_planner_rejects_disabled_strategy() -> None:
    planner = _planner(["POST_ONLY"])
    with pytest.raises(InfeasiblePlan):
        planner.plan(signal=_signal("TWAP"), market_snapshot=_snapshot(), price_band_hint=None, ttl_hint=None)
