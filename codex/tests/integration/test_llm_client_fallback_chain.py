import asyncio

from codex.config.models import Settings
from codex.contracts.features import DeterministicFeatures, MetaContext
from codex.contracts.sentiment import AggregatedSentiment
from codex.llm_risk.client import LLMRiskClient, ProviderRegistry
from codex.llm_risk.providers.base import LLMProvider
from codex.llm_risk.providers.errors import ProviderResponseError, ProviderTransportError


class TimeoutProvider(LLMProvider):
    name = "qwen"

    async def complete(self, payload):
        raise ProviderTransportError("timeout")


class SuccessfulFallbackProvider(LLMProvider):
    name = "deepseek"

    async def complete(self, payload):
        return {
            "verdict": "CONFIRM",
            "size_multiplier": 0.9,
            "risk_tags": [],
            "short_reason": "fallback succeeded",
            "prompt_version": payload["prompt_version"],
            "cache_hit": False,
            "latency_ms": 0,
            "is_fallback": False,
            "stale_correlation": payload.get("stale_correlation", False),
        }


class BrokenFallbackProvider(LLMProvider):
    name = "claude"

    async def complete(self, payload):
        raise ProviderResponseError("invalid json")


class FailingFallbackProvider(LLMProvider):
    name = "deepseek"

    async def complete(self, payload):
        raise ProviderResponseError("deepseek failure")


def _base_payload():
    features = DeterministicFeatures(regime="normal", rsi_14=44, atr_pct=0.3, spread_bps=2)
    sentiment = AggregatedSentiment(
        sentiment_score=0.1,
        event_severity="low",
        confidence=0.5,
        sources_confirmed=1,
    )
    meta = MetaContext()
    return features, sentiment, meta


def test_llm_client_uses_fallback(settings: Settings):
    settings.llm.primary = "qwen"
    settings.llm.fallback_chain = ["deepseek", "claude"]
    registry = ProviderRegistry([TimeoutProvider(), SuccessfulFallbackProvider(), BrokenFallbackProvider()])
    client = LLMRiskClient(settings, registry=registry)
    features, sentiment, meta = _base_payload()
    decision = asyncio.run(client.evaluate(features=features, sentiment=sentiment, meta=meta))
    assert decision.is_fallback is True
    assert decision.size_multiplier <= settings.llm_risk.fallback.max_size_multiplier
    assert "llm_fallback" in decision.risk_tags


def test_llm_client_fail_closed(settings: Settings):
    settings.llm.primary = "qwen"
    settings.llm.fallback_chain = ["deepseek", "claude"]
    registry = ProviderRegistry([TimeoutProvider(), FailingFallbackProvider(), BrokenFallbackProvider()])
    client = LLMRiskClient(settings, registry=registry)
    base_features, sentiment, meta = _base_payload()
    data = base_features.model_dump()
    data["spread_bps"] = base_features.spread_bps + 5
    features = DeterministicFeatures(**data)
    decision = asyncio.run(client.evaluate(features=features, sentiment=sentiment, meta=meta))
    assert decision.verdict in {"DOWNGRADE", "BLOCK"}
    assert decision.is_fallback is True
    assert decision.size_multiplier <= settings.llm_risk.fallback.max_size_multiplier
