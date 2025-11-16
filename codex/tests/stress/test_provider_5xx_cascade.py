import asyncio

from codex.config.models import Settings
from codex.contracts.features import DeterministicFeatures, MetaContext
from codex.contracts.sentiment import AggregatedSentiment
from codex.llm_risk.client import LLMRiskClient, ProviderRegistry
from codex.llm_risk.providers.base import LLMProvider
from codex.llm_risk.providers.errors import ProviderResponseError


class ErrorProvider(LLMProvider):
    name = "qwen"

    async def complete(self, payload):
        raise ProviderResponseError("server error")


def test_provider_error_triggers_fallback(settings: Settings):
    registry = ProviderRegistry([ErrorProvider()])
    settings.llm.primary = "qwen"
    settings.llm.fallback_chain = []
    client = LLMRiskClient(settings, registry=registry)
    features = DeterministicFeatures(regime="normal", rsi_14=41, atr_pct=0.2, spread_bps=2)
    sentiment = AggregatedSentiment(sentiment_score=0.0, event_severity="none", confidence=0.5, sources_confirmed=0)
    meta = MetaContext()
    decision = asyncio.run(client.evaluate(features=features, sentiment=sentiment, meta=meta))
    assert decision.is_fallback
