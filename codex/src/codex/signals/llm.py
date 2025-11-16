from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from jsonschema import validate as jsonschema_validate

from ..config.models import Settings
from ..contracts.features import MetaContext
from ..contracts.sentiment import AggregatedSentiment
from ..llm.provider_registry import ProviderRegistry, build_registry, provider_order
from ..llm_risk.providers.errors import ProviderError, ProviderResponseError
from ..monitoring.metrics import adapter_error_counter, fallback_counter, json_validation_fail_counter, llm_latency
from ..contracts.verdict import RiskAssessment
from .models import MetaDecision, SignalCandidate, SignalExplanation


@dataclass
class StructuredResponse:
    payload: Dict[str, object]
    provider: str
    latency_ms: int
    is_fallback: bool


class StructuredLLMClient:
    def __init__(
        self,
        settings: Settings,
        prompt_path: Path,
        schema_path: Path,
        *,
        registry: ProviderRegistry | None = None,
    ) -> None:
        self.settings = settings
        self.system_prompt = prompt_path.read_text(encoding="utf-8")
        self.schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.registry = registry or build_registry(settings, self.system_prompt)

    async def invoke(self, payload: Dict[str, object], *, min_success: int = 1) -> List[StructuredResponse]:
        responses: List[StructuredResponse] = []
        last_provider: str | None = None
        for index, provider_name in enumerate(provider_order(self.settings)):
            provider = self.registry.get(provider_name)
            last_provider = provider_name
            started = time.perf_counter()
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
            except Exception:
                json_validation_fail_counter.labels(provider=provider_name).inc()
                continue
            latency_ms = int((time.perf_counter() - started) * 1000)
            llm_latency.labels(provider=provider_name).observe(latency_ms)
            if index > 0:
                fallback_counter.labels(provider=provider_name).inc()
            responses.append(
                StructuredResponse(
                    payload=raw,
                    provider=provider_name,
                    latency_ms=latency_ms,
                    is_fallback=index > 0,
                )
            )
            if len(responses) >= min_success:
                break
        if not responses and last_provider:
            fallback_counter.labels(provider=last_provider).inc()
        return responses


class SignalAnalystClient(StructuredLLMClient):
    def __init__(
        self,
        settings: Settings,
        *,
        registry: ProviderRegistry | None = None,
    ) -> None:
        super().__init__(
            settings,
            prompt_path=settings.analyst_prompt_path(),
            schema_path=settings.analyst_schema_path(),
            registry=registry,
        )

    async def explain(
        self,
        candidate: SignalCandidate,
        risk: RiskAssessment,
        sentiment: AggregatedSentiment,
        meta: MetaContext,
    ) -> SignalExplanation:
        payload = {
            "candidate": candidate.model_dump(),
            "risk": risk.model_dump(),
            "sentiment": sentiment.model_dump(),
            "meta": meta.model_dump(),
        }
        responses = await self.invoke(payload)
        if not responses:
            return SignalExplanation(
                explanation="LLM analyst unavailable; use strategy defaults",
                confidence=0.2,
                key_drivers=["Fallback due to LLM error"],
                risk_callouts=["llm_fallback"],
                timeframe_alignment="intra",
                recommended_action="defer",
                short_summary="LLM analyst fallback",
            )
        return SignalExplanation.model_validate(responses[0].payload)


class MetaJudgeClient(StructuredLLMClient):
    def __init__(
        self,
        settings: Settings,
        *,
        registry: ProviderRegistry | None = None,
    ) -> None:
        super().__init__(
            settings,
            prompt_path=settings.meta_judge_prompt_path(),
            schema_path=settings.meta_judge_schema_path(),
            registry=registry,
        )
        self.consensus_policy = settings.signal_system.consensus

    async def judge(
        self,
        candidate: SignalCandidate,
        risk: RiskAssessment,
        explanation: SignalExplanation,
        sentiment: AggregatedSentiment,
        meta: MetaContext,
    ) -> MetaDecision:
        payload = {
            "candidate": candidate.model_dump(),
            "risk": risk.model_dump(),
            "explanation": explanation.model_dump(),
            "sentiment": sentiment.model_dump(),
            "meta": meta.model_dump(),
        }
        require_consensus = sentiment.event_severity.lower() == self.consensus_policy.critical_event_severity.lower()
        min_success = self.consensus_policy.min_agree if require_consensus else 1
        responses = await self.invoke(payload, min_success=min_success)
        if not responses:
            return self._fallback_decision()
        decisions = [MetaDecision.model_validate(resp.payload) for resp in responses]
        return self._apply_consensus(decisions, require_consensus)

    def _apply_consensus(self, decisions: List[MetaDecision], require_consensus: bool) -> MetaDecision:
        if len(decisions) == 1 and not require_consensus:
            return decisions[0]
        publish_votes = sum(1 for d in decisions if d.publish)
        if require_consensus and publish_votes < self.consensus_policy.min_agree:
            base = decisions[0]
            tags = set(base.recommended_tags)
            tags.add("llm_disagreement")
            return base.model_copy(
                update={
                    "publish": False,
                    "final_verdict": "DOWNGRADE",
                    "recommended_tags": sorted(tags),
                    "status_note": base.status_note + " Consensus not met.",
                }
            )
        final = decisions[0]
        if any(dec.final_verdict == "BLOCK" for dec in decisions):
            final = next(dec for dec in decisions if dec.final_verdict == "BLOCK")
        elif len({dec.final_verdict for dec in decisions}) > 1:
            tags = set(final.recommended_tags)
            tags.add("llm_disagreement")
            final = final.model_copy(
                update={
                    "recommended_tags": sorted(tags),
                    "publish": False,
                    "final_verdict": "DOWNGRADE",
                    "status_note": final.status_note + " Providers disagree.",
                }
            )
        return final

    @staticmethod
    def _fallback_decision() -> MetaDecision:
        return MetaDecision(
            final_verdict="DOWNGRADE",
            priority="high",
            warnings=["LLM consensus unavailable"],
            llm_confidence=0.2,
            status_note="Fallback decision triggered",
            publish=False,
            annotations=["llm_fallback"],
            recommended_tags=["llm_fallback"],
            explanation="Meta judge unavailable",
        )
