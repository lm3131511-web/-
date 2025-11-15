import asyncio

from codex.config.models import Settings
from codex.contracts.features import DeterministicFeatures, MetaContext
from codex.contracts.sentiment import AggregatedSentiment
from codex.llm_risk.client import LLMRiskClient, ProviderRegistry
from codex.llm_risk.providers.base import LLMProvider


class DummyProvider(LLMProvider):
    name = "qwen"

    async def complete(self, payload):
        return {
            "verdict": "CONFIRM",
            "size_multiplier": 0.75,
            "risk_tags": [],
            "short_reason": "dummy provider",
            "prompt_version": payload["prompt_version"],
            "cache_hit": False,
            "latency_ms": 0,
            "is_fallback": False,
            "stale_correlation": payload.get("stale_correlation", False),
        }

def test_end_to_end_flow(settings: Settings):
    settings.llm.primary = "qwen"
    settings.llm.fallback_chain = []
    registry = ProviderRegistry([DummyProvider()])
    client = LLMRiskClient(settings, registry=registry)
    features = DeterministicFeatures(regime="normal", rsi_14=45, atr_pct=0.2, spread_bps=3)
    sentiment = AggregatedSentiment(sentiment_score=-0.2, event_severity="low", confidence=0.6, sources_confirmed=2)
    meta = MetaContext(mode="live")
    decision = asyncio.run(client.evaluate(features=features, sentiment=sentiment, meta=meta))
    assert decision.verdict in {"CONFIRM", "DOWNGRADE", "BLOCK"}
    assert decision.prompt_version == "v2.2.0"
