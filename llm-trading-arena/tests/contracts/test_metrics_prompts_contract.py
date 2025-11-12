from __future__ import annotations

import asyncio

from src.config.loader import load_config
from src.llm.stages import build_stage_runners
from src.monitoring.metrics import GLOBAL_METRICS


def test_metrics_expose_prompt_metadata() -> None:
    asyncio.run(_exercise())


async def _exercise() -> None:
    GLOBAL_METRICS.reset()
    config = load_config("config.sample.yaml")
    config.llm.mock_mode = True
    limits = {
        "ttl_sec_range": list(config.execution.ttl_sec_range),
        "max_spread_bps": config.execution.max_spread_bps,
        "max_on_demand_features": config.llm.max_on_demand_features,
    }
    runners = build_stage_runners(config.llm, limits=limits)
    snapshot = {
        "symbol": "BTCUSDT",
        "bid": 100.0,
        "ask": 100.4,
        "mid_price": 100.2,
        "spread_bps": 5.0,
        "top_depth_usd": 2_500_000.0,
        "micro_price_delta": 0.015,
        "order_imbalance": 0.25,
        "micro_volatility_q": 0.03,
        "last_trades_summary": "balanced",
    }
    for runner in runners:
        await runner.run(snapshot, regime="stable_trend", risk_level=0.25)
    metrics = GLOBAL_METRICS.snapshot()
    prompt_versions = metrics.get("prompt_versions")
    prompt_hashes = metrics.get("prompt_hashes")
    assert set(prompt_versions.keys()) >= {"A", "B", "C"}
    assert set(prompt_hashes.keys()) >= {"A", "B", "C"}
    for stage in ("A", "B", "C"):
        assert prompt_versions[stage]
        assert len(prompt_hashes[stage]) == 16
    GLOBAL_METRICS.reset()
