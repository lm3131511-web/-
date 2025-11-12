from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Iterable

from jsonschema import validate as jsonschema_validate

from ..config.models import Settings
from ..contracts.features import DeterministicFeatures, MetaContext
from ..contracts.llm import LLMVerdict
from ..contracts.sentiment import AggregatedSentiment
from ..contracts.verdict import RiskAssessment
from ..features.deltas import FingerprintEvaluator
from ..llm_risk.cache import TTLCache
from ..llm_risk.cache_persist import SQLiteCachePersistor, PersistedEntry
from ..utils.ids import fingerprint
from ..utils.time import utc_now
from .providers.base import LLMProvider
from .providers.claude_sonnet import ClaudeSonnetProvider
from .providers.deepseek import DeepSeekProvider
from .providers.qwen import QwenProvider
from .providers.local_llama import LocalLlamaProvider


class ProviderRegistry:
    def __init__(self, providers: Iterable[LLMProvider]) -> None:
        self._providers = {provider.name: provider for provider in providers}

    def get(self, name: str) -> LLMProvider:
        if name not in self._providers:
            raise KeyError(f"Provider {name} is not registered")
        return self._providers[name]


class LockManager:
    def __init__(self) -> None:
        self._locks: Dict[str, asyncio.Lock] = {}

    def acquire(self, key: str) -> asyncio.Lock:
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]


class LLMRiskClient:
    def __init__(
        self,
        settings: Settings,
        registry: ProviderRegistry | None = None,
        cache: TTLCache[RiskAssessment] | None = None,
        persistor: SQLiteCachePersistor | None = None,
    ) -> None:
        self.settings = settings
        self.registry = registry or ProviderRegistry(
            providers=[
                ClaudeSonnetProvider(),
                DeepSeekProvider(),
                QwenProvider(),
                LocalLlamaProvider(),
            ]
        )
        cache_conf = settings.llm_risk.cache
        self.cache = cache or TTLCache[RiskAssessment](ttl_sec=cache_conf.ttl_sec, max_items=cache_conf.max_items)
        self.persistor = persistor or SQLiteCachePersistor(cache_conf.persistence.path)
        ff_conf = settings.llm_risk.feature_fingerprint
        self.fingerprint = FingerprintEvaluator(deltas=ff_conf.deltas, cooldown_sec=settings.llm_risk.cooldown_sec)
        schema_path = Path(settings.json_schema_path())
        self.schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.lock_manager = LockManager()

    async def evaluate(
        self,
        *,
        features: DeterministicFeatures,
        sentiment: AggregatedSentiment,
        meta: MetaContext,
    ) -> RiskAssessment:
        payload = {
            field: getattr(features, field)
            for field in self.settings.llm_risk.feature_fingerprint.fields
            if hasattr(features, field)
        }
        payload.update(
            {
                "sentiment_score": sentiment.sentiment_score,
                "event_severity": sentiment.event_severity,
            }
        )
        key = fingerprint(payload)
        cached = self.cache.get(key)
        if cached:
            return cached.model_copy(update={"cache_hit": True})
        persisted = self.persistor.read(key)
        if persisted and persisted.expires_at > utc_now().timestamp():
            verdict = RiskAssessment.model_validate(persisted.value)
            self.cache.set(key, verdict)
            return verdict.model_copy(update={"cache_hit": True})

        if not self.fingerprint.should_invoke(features, sentiment):
            fallback = RiskAssessment(
                verdict="CONFIRM",
                size_multiplier=1.0,
                risk_tags=[],
                short_reason="cooldown active",
                prompt_version=self.settings.prompt_version,
                cache_hit=False,
                latency_ms=0,
                is_fallback=False,
                stale_correlation=False,
            )
            self.cache.set(key, fallback)
            return fallback

        lock = self.lock_manager.acquire(key)
        async with lock:
            start = time.perf_counter()
            provider = self.registry.get(self.settings.llm.primary)
            request_payload = {
                "features": features.model_dump(),
                "sentiment": sentiment.model_dump(),
                "meta": meta.model_dump(),
                "prompt_version": self.settings.prompt_version,
                "stale_correlation": bool(
                    features.correlation_ts_seconds
                    and features.correlation_ts_seconds > 0
                    and (utc_now().timestamp() - features.correlation_ts_seconds) > 600
                ),
            }
            try:
                raw = await provider.complete(request_payload)
                jsonschema_validate(raw, self.schema)
                verdict = LLMVerdict.model_validate(raw)
            except Exception as exc:  # broad catch for fail-closed
                fallback = self._fallback_decision(str(exc))
                self.cache.set(key, fallback)
                return fallback
            latency_ms = int((time.perf_counter() - start) * 1000)
            verdict_payload = verdict.model_dump()
            verdict_payload["prompt_version"] = self.settings.prompt_version
            verdict_payload["latency_ms"] = latency_ms
            assessment = RiskAssessment(**verdict_payload)
            self.cache.set(key, assessment)
            self.persistor.write(
                PersistedEntry(
                    key=key,
                    value=assessment.model_dump(),
                    expires_at=utc_now().timestamp() + self.settings.llm_risk.cache.ttl_sec,
                )
            )
            self.fingerprint.update(features, sentiment)
            return assessment

    def _fallback_decision(self, reason: str) -> RiskAssessment:
        fallback_mult = min(0.3, self.settings.llm_risk.fallback.max_size_multiplier)
        return RiskAssessment(
            verdict="DOWNGRADE",
            size_multiplier=fallback_mult,
            risk_tags=["llm_fallback"],
            short_reason=reason[:240] or "llm fallback",
            prompt_version=self.settings.prompt_version,
            cache_hit=False,
            latency_ms=0,
            is_fallback=True,
            stale_correlation=False,
        )
