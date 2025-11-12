from __future__ import annotations

import asyncio
from pathlib import Path

from src.config.loader import load_config
from src.llm.prompt_loader import clear_prompt_cache
from src.llm.stages import build_stage_runners
from src.monitoring.metrics import GLOBAL_METRICS


def test_prompt_hash_updates_after_template_change() -> None:
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
    runner_a = next(r for r in runners if r.config.name == "A")
    snapshot = {
        "symbol": "BTCUSDT",
        "bid": 100.0,
        "ask": 100.5,
        "mid_price": 100.25,
        "spread_bps": 6.0,
        "top_depth_usd": 2_000_000.0,
        "micro_price_delta": 0.01,
        "order_imbalance": 0.2,
        "micro_volatility_q": 0.02,
        "last_trades_summary": "buyers aggressive",
    }
    regime = "stable_trend"
    risk_level = 0.3
    await runner_a.run(snapshot, regime=regime, risk_level=risk_level)
    metrics_before = GLOBAL_METRICS.snapshot()
    hash_before = metrics_before["prompt_hashes"]["A"]
    assert metrics_before["prompt_versions"]["A"] == runner_a.config.prompt_version

    prompt_path = Path("prompts/analyst_A.md")
    original = prompt_path.read_text(encoding="utf-8")
    prompt_path.write_text(original + "\n# touch", encoding="utf-8")
    try:
        clear_prompt_cache()
        response = await runner_a.run(snapshot, regime=regime, risk_level=risk_level)
    finally:
        prompt_path.write_text(original, encoding="utf-8")
        clear_prompt_cache()

    metrics_after = GLOBAL_METRICS.snapshot()
    hash_after = metrics_after["prompt_hashes"]["A"]
    assert hash_after != hash_before
    assert response.prompt_hash == hash_after
    GLOBAL_METRICS.reset()
