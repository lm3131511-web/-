import pytest

from src.core.contracts import Signal
from src.exec.planner import ExecutionPlanner, InfeasiblePlan


def make_signal(strategy: str) -> Signal:
    return Signal(
        symbol="BTCUSDT",
        side="BUY",
        strategy=strategy,
        kelly_base=0.4,
        safety_multiplier=0.8,
        final_size_frac=0.12,
        p_final=0.62,
        uncertainty=0.2,
        reasoning="test",
    )


def test_execution_planner_respects_llm_strategy() -> None:
    planner = ExecutionPlanner(
        {
            "enforce_exchange_filters": True,
            "ttl_sec_range": [30, 120],
            "price_bands_vol_mult": 2.0,
            "minimal_notional_usd": 10,
            "low_top_depth_usd": 1_000_000,
            "strategies": ["POST_ONLY", "IOC"],
            "strategy_thresholds": {},
            "post_only_queue_penalty_bps": 0.5,
        }
    )
    market = {"mid": 100.0, "volatility": 0.01}
    signal = make_signal("POST_ONLY")
    plan = planner.plan(
        signal=signal,
        market_snapshot=market,
        price_band_bps=10.0,
        ttl_hint=45,
        notional_usd=12.0,
    )
    assert plan.legs[0].strategy == "POST_ONLY"
    assert plan.legs[0].ttl_seconds == 45
    assert plan.legs[0].price > 0


def test_execution_planner_rejects_disabled_strategy() -> None:
    planner = ExecutionPlanner(
        {
            "enforce_exchange_filters": True,
            "ttl_sec_range": [30, 120],
            "price_bands_vol_mult": 2.0,
            "minimal_notional_usd": 10,
            "low_top_depth_usd": 1_000_000,
            "strategies": ["POST_ONLY"],
            "strategy_thresholds": {},
            "post_only_queue_penalty_bps": 0.5,
        }
    )
    with pytest.raises(InfeasiblePlan):
        planner.plan(
            signal=make_signal("TWAP"),
            market_snapshot={"mid": 100.0, "volatility": 0.01},
            price_band_bps=None,
            ttl_hint=None,
            notional_usd=12.0,
        )
