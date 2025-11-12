import asyncio

from codex.config.models import Settings
from codex.contracts.features import DeterministicFeatures, MetaContext
from codex.contracts.sentiment import AggregatedSentiment
from codex.llm_risk.client import LLMRiskClient
from codex.llm_risk.providers.base import LLMProvider
from codex.llm_risk.client import ProviderRegistry


class BrokenProvider(LLMProvider):
    name = "broken"

    async def complete(self, payload):
        return {"verdict": "CONFIRM"}


def test_invalid_schema_triggers_fallback(settings: Settings):
    registry = ProviderRegistry([BrokenProvider()])
    settings.llm.primary = "broken"
    client = LLMRiskClient(settings, registry=registry)
    features = DeterministicFeatures(regime="normal", rsi_14=45, atr_pct=0.2, spread_bps=3)
    sentiment = AggregatedSentiment(sentiment_score=0.1, event_severity="low", confidence=0.5, sources_confirmed=1)
    meta = MetaContext()
    result = asyncio.run(client.evaluate(features=features, sentiment=sentiment, meta=meta))
    assert result.is_fallback
    assert result.size_multiplier <= 0.3
