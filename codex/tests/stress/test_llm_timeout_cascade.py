import asyncio

from codex.config.models import Settings
from codex.contracts.features import DeterministicFeatures, MetaContext
from codex.contracts.sentiment import AggregatedSentiment
from codex.llm_risk.client import LLMRiskClient, ProviderRegistry
from codex.llm_risk.providers.base import LLMProvider
from codex.llm_risk.providers.errors import ProviderTransportError


class TimeoutProvider(LLMProvider):
    name = "qwen"

    async def complete(self, payload):
        raise ProviderTransportError("provider timeout")


def test_timeout_falls_back(settings: Settings):
    registry = ProviderRegistry([TimeoutProvider()])
    settings.llm.primary = "qwen"
    settings.llm.fallback_chain = []
    client = LLMRiskClient(settings, registry=registry)
    features = DeterministicFeatures(regime="normal", rsi_14=44, atr_pct=0.3, spread_bps=3)
    sentiment = AggregatedSentiment(sentiment_score=0.0, event_severity="none", confidence=0.5, sources_confirmed=0)
    meta = MetaContext()
    decision = asyncio.run(client.evaluate(features=features, sentiment=sentiment, meta=meta))
    assert decision.is_fallback
    assert decision.size_multiplier <= settings.llm_risk.fallback.max_size_multiplier
