from __future__ import annotations

import asyncio
import json
import time
from typing import Dict, List

from jsonschema import validate as jsonschema_validate

from ..config.models import Settings
from ..contracts.features import DeterministicFeatures, MetaContext
from ..contracts.llm import LLMVerdict
from ..contracts.sentiment import AggregatedSentiment
from ..contracts.verdict import RiskAssessment
from ..features.deltas import FingerprintEvaluator
from ..features.selectors import FeatureSelector
from ..llm.provider_registry import ProviderRegistry, build_registry, provider_order
from ..llm_risk.cache import TTLCache
from ..llm_risk.cache_persist import SQLiteCachePersistor, PersistedEntry
from ..monitoring.metrics import (
    adapter_error_counter,
    cache_hit_counter,
    cache_persist_hit_counter,
    cooldown_skip_counter,
    correlation_stale_counter,
    fallback_counter,
    json_validation_fail_counter,
    llm_latency,
    size_multiplier_histogram,
    verdict_counter,
)
from ..persistence.models import DecisionRecord
from ..persistence.store import DecisionLog
from ..utils.ids import fingerprint
from ..utils.time import utc_now
from .providers.errors import ProviderError, ProviderResponseError


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
        decision_log: DecisionLog | None = None,
    ) -> None:
        self.settings = settings
        self.system_prompt = settings.prompt_path().read_text(encoding="utf-8")
        self.registry = registry or build_registry(self.settings, self.system_prompt)
        cache_conf = settings.llm_risk.cache
        self.cache = cache or TTLCache[RiskAssessment](ttl_sec=cache_conf.ttl_sec, max_items=cache_conf.max_items)
        self.persistor = persistor or SQLiteCachePersistor(cache_conf.persistence.path)
        ff_conf = settings.llm_risk.feature_fingerprint
        self.fingerprint = FingerprintEvaluator(deltas=ff_conf.deltas, cooldown_sec=settings.llm_risk.cooldown_sec)
        self.selector = FeatureSelector(ff_conf)
        schema_path = settings.json_schema_path()
        self.schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.lock_manager = LockManager()
        self.decision_log = decision_log

    async def evaluate(
        self,
        *,
        features: DeterministicFeatures,
        sentiment: AggregatedSentiment,
        meta: MetaContext,
    ) -> RiskAssessment:
        payload = self.selector.select(features)
        payload.update(
            {
                "sentiment_score": sentiment.sentiment_score,
                "event_severity": sentiment.event_severity,
            }
        )
        key = fingerprint(payload)
        cached = self.cache.get(key)
        if cached:
            cache_hit_counter.labels(source="memory").inc()
            cached_hit = cached.model_copy(update={"cache_hit": True})
            self._log_decision(key, cached_hit)
            return cached_hit
        persisted = self.persistor.read(key)
        if persisted and persisted.expires_at > utc_now().timestamp():
            verdict = RiskAssessment.model_validate(persisted.value)
            self.cache.set(key, verdict)
            cache_persist_hit_counter.inc()
            cache_hit_counter.labels(source="persisted").inc()
            persisted_hit = verdict.model_copy(update={"cache_hit": True})
            self._log_decision(key, persisted_hit)
            return persisted_hit

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
            cooldown_skip_counter.inc()
            self._log_decision(key, fallback)
            return fallback

        lock = self.lock_manager.acquire(key)
        async with lock:
            stale_correlation = bool(
                features.correlation_ts_seconds
                and features.correlation_ts_seconds > 0
                and (utc_now().timestamp() - features.correlation_ts_seconds) > 900
            )
            if stale_correlation:
                correlation_stale_counter.inc()
            request_payload = {
                "features": features.model_dump(),
                "sentiment": sentiment.model_dump(),
                "meta": meta.model_dump(),
                "prompt_version": self.settings.prompt_version,
                "stale_correlation": stale_correlation,
            }
            assessment, provider_name = await self._attempt_with_fallbacks(request_payload)
            if assessment is None:
                fallback = self._fallback_decision("llm failure")
                self.cache.set(key, fallback)
                self._log_decision(key, fallback, provider_name)
                return fallback
            if stale_correlation:
                assessment = assessment.model_copy(update={"stale_correlation": True})
            self.cache.set(key, assessment)
            self.persistor.write(
                PersistedEntry(
                    key=key,
                    value=assessment.model_dump(),
                    expires_at=utc_now().timestamp() + self.settings.llm_risk.cache.ttl_sec,
                )
            )
            self.fingerprint.update(features, sentiment)
            size_multiplier_histogram.observe(assessment.size_multiplier)
            self._log_decision(key, assessment, provider_name)
            return assessment

    def _fallback_decision(self, reason: str) -> RiskAssessment:
        fallback_mult = min(0.3, self.settings.llm_risk.fallback.max_size_multiplier)
        assessment = RiskAssessment(
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
        size_multiplier_histogram.observe(assessment.size_multiplier)
        return assessment

    def _log_decision(self, fingerprint_hash: str, assessment: RiskAssessment, provider: str | None = None) -> None:
        if not self.decision_log:
            return
        record = DecisionRecord(
            prompt_version=self.settings.prompt_version,
            provider=provider or self.settings.llm.primary,
            verdict=assessment.verdict,
            size_multiplier=assessment.size_multiplier,
            risk_tags=assessment.risk_tags,
            cache_hit=assessment.cache_hit,
            latency_ms=assessment.latency_ms,
            fingerprint_hash=fingerprint_hash,
            is_fallback=assessment.is_fallback,
            stale_correlation=assessment.stale_correlation,
            short_reason=assessment.short_reason,
        )
        self.decision_log.write_decision(record)

    def _build_registry(self) -> ProviderRegistry:
        providers: List[LLMProvider] = [
            QwenProvider(self.settings, self.system_prompt),
            DeepSeekProvider(self.settings, self.system_prompt),
            ClaudeSonnetProvider(self.settings, self.system_prompt),
        ]
        return ProviderRegistry(providers)

    async def _attempt_with_fallbacks(
        self, payload: Dict[str, Dict[str, object]]
    ) -> tuple[RiskAssessment | None, str | None]:
        attempts = self._provider_order()
        last_provider: str | None = None
        for index, provider_name in enumerate(attempts):
            provider = self.registry.get(provider_name)
            last_provider = provider_name
            attempt_start = time.perf_counter()
            try:
                raw = await provider.complete(payload)
            except ProviderResponseError:
                adapter_error_counter.labels(provider=provider_name).inc()
                json_validation_fail_counter.labels(provider=provider_name).inc()
                continue
            except ProviderError:
                adapter_error_counter.labels(provider=provider_name).inc()
                continue
            try:
                jsonschema_validate(raw, self.schema)
                verdict = LLMVerdict.model_validate(raw)
            except Exception:
                json_validation_fail_counter.labels(provider=provider_name).inc()
                adapter_error_counter.labels(provider=provider_name).inc()
                continue
            latency_ms = int((time.perf_counter() - attempt_start) * 1000)
            llm_latency.labels(provider=provider_name).observe(latency_ms)
            verdict_payload = verdict.model_dump()
            verdict_payload["prompt_version"] = self.settings.prompt_version
            verdict_payload["latency_ms"] = latency_ms
            assessment = RiskAssessment(**verdict_payload)
            if index > 0:
                fallback_mult = min(assessment.size_multiplier, self.settings.llm_risk.fallback.max_size_multiplier)
                tags = set(assessment.risk_tags)
                tags.add("llm_fallback")
                assessment = assessment.model_copy(
                    update={
                        "size_multiplier": fallback_mult,
                        "is_fallback": True,
                        "risk_tags": sorted(tags),
                    }
                )
                fallback_counter.labels(provider=provider_name).inc()
            verdict_counter.labels(provider=provider_name, verdict=assessment.verdict).inc()
            return assessment, provider_name
        if last_provider:
            fallback_counter.labels(provider=last_provider).inc()
        return None, last_provider

    def _provider_order(self) -> List[str]:
        return provider_order(self.settings)
