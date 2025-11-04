import asyncio

from src.config.loader import load_config
from src.llm.stages import build_stage_runners


async def _run_stage(mode: str):
    config = load_config("config.sample.yaml")
    config.llm.mock_mode = True
    config.llm.stages["A"].mode = mode
    limits = {
        "ttl_sec_range": list(config.execution.ttl_sec_range),
        "max_spread_bps": config.execution.max_spread_bps,
        "max_on_demand_features": config.llm.max_on_demand_features,
    }
    runner = next(r for r in build_stage_runners(config.llm, limits=limits) if r.config.name == "A")
    snapshot = {
        "symbol": "BTCUSDT",
        "bid": 100.0,
        "ask": 100.5,
        "mid_price": 100.25,
        "spread_bps": 5.0,
        "top_depth_usd": 1_500_000.0,
        "micro_price_delta": 0.01,
        "order_imbalance": 0.2,
        "micro_volatility_q": 0.02,
        "last_trades_summary": "buyers active",
    }
    response = await runner.run(snapshot, regime="stable_trend", risk_level=0.3)
    return runner.config.provider.last_completion_meta, response


def test_stub_and_real_modes_share_fallbacks() -> None:
    stub_meta, stub_response = asyncio.run(_run_stage("stub"))
    assert stub_meta["mock_fallback_used"] is False
    assert stub_response.direction in {"BUY", "SELL", "FLAT"}

    real_meta, real_response = asyncio.run(_run_stage("real"))
    assert real_meta["mock_fallback_used"] is True
    assert real_response.direction in {"BUY", "SELL", "FLAT"}
