import asyncio

from codex.config.models import Settings
from codex.contracts.features import DeterministicFeatures, MetaContext
from codex.contracts.sentiment import AggregatedSentiment
from codex.llm_risk.client import LLMRiskClient, ProviderRegistry
from codex.llm_risk.providers.base import LLMProvider
from codex.llm_risk.providers.errors import ProviderTransportError


class FlakyProvider(LLMProvider):
    name = "qwen"

    async def complete(self, payload):
        raise ProviderTransportError("transient failure")


def test_retry_recovers(settings: Settings):
    provider = FlakyProvider()
    settings.llm.primary = provider.name
    settings.llm.fallback_chain = []
    registry = ProviderRegistry([provider])
    client = LLMRiskClient(settings, registry=registry)
    features = DeterministicFeatures(regime="normal", rsi_14=44, atr_pct=0.3, spread_bps=2)
    sentiment = AggregatedSentiment(sentiment_score=0.1, event_severity="low", confidence=0.5, sources_confirmed=1)
    meta = MetaContext()
    decision = asyncio.run(client.evaluate(features=features, sentiment=sentiment, meta=meta))
    assert decision.is_fallback
