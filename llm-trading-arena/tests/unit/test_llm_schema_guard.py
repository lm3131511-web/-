from __future__ import annotations

import asyncio

import pytest

from src.config.loader import load_config
from src.llm.stages import build_stage_runners
from src.monitoring.metrics import GLOBAL_METRICS


def test_invalid_completion_falls_back_to_flat() -> None:
    asyncio.run(_exercise())


async def _exercise() -> None:
    GLOBAL_METRICS.reset()
    config = load_config("config.sample.yaml")
    config.llm.mock_mode = False
    limits = {
        "ttl_sec_range": list(config.execution.ttl_sec_range),
        "max_spread_bps": config.execution.max_spread_bps,
        "max_on_demand_features": config.llm.max_on_demand_features,
    }
    runners = build_stage_runners(config.llm, limits=limits)
    runner_a = next(r for r in runners if r.config.name == "A")
    snapshot = {
        "symbol": "BTCUSDT",
        "bid": 100.0,
        "ask": 101.0,
        "mid_price": 100.5,
        "spread_bps": 12.0,
        "top_depth_usd": 800_000.0,
        "micro_price_delta": -0.02,
        "order_imbalance": -0.4,
        "micro_volatility_q": 0.05,
        "last_trades_summary": "sellers dominate",
    }
    response = await runner_a.run(snapshot, regime="volatile", risk_level=0.8)
    metrics = GLOBAL_METRICS.snapshot()
    assert response.direction == "FLAT"
    assert response.size_hint_frac == 0.0
    assert metrics["llm_json_repair_rate"] == pytest.approx(1.0, rel=0.0)
    GLOBAL_METRICS.reset()
