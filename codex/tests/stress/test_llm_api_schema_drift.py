import asyncio

from codex.config.models import Settings
from codex.contracts.features import DeterministicFeatures, MetaContext
from codex.contracts.sentiment import AggregatedSentiment
from codex.llm_risk.client import LLMRiskClient, ProviderRegistry
from codex.llm_risk.providers.base import LLMProvider


class DriftProvider(LLMProvider):
    name = "drift"

    async def complete(self, payload):
        return {
            "verdict": "CONFIRM",
            "size_multiplier": 1.1,
            "short_reason": "too large",
        }


def test_schema_drift_detected(settings: Settings):
    registry = ProviderRegistry([DriftProvider()])
    settings.llm.primary = "drift"
    client = LLMRiskClient(settings, registry=registry)
    features = DeterministicFeatures(regime="normal", rsi_14=41, atr_pct=0.2, spread_bps=2)
    sentiment = AggregatedSentiment(sentiment_score=0.0, event_severity="none", confidence=0.5, sources_confirmed=0)
    meta = MetaContext()
    decision = asyncio.run(client.evaluate(features=features, sentiment=sentiment, meta=meta))
    assert decision.is_fallback
