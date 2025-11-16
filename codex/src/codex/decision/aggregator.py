from __future__ import annotations

import asyncio

from ..config.models import Settings
from ..contracts.features import DeterministicFeatures, MetaContext
from ..contracts.sentiment import AggregatedSentiment
from ..contracts.verdict import RiskAssessment
from ..llm_risk.client import LLMRiskClient
from .rules import evaluate_rules


def build_risk_assessment(
    *,
    settings: Settings,
    client: LLMRiskClient,
    features: DeterministicFeatures,
    sentiment: AggregatedSentiment,
    meta: MetaContext,
) -> RiskAssessment:
    gate = evaluate_rules(config=settings.risk_rules, features=features, sentiment=sentiment)
    if gate:
        assessment = RiskAssessment(
            verdict=gate.verdict,
            size_multiplier=gate.size_multiplier,
            risk_tags=gate.risk_tags,
            short_reason=gate.reason,
            prompt_version=settings.prompt_version,
            cache_hit=False,
            latency_ms=0,
            is_fallback=False,
            stale_correlation=gate.stale_correlation,
        )
        if gate.stale_correlation:
            assessment = assessment.capped(settings.risk_rules.correlation.stale_penalty_multiplier)
        return assessment
    return asyncio.run(client.evaluate(features=features, sentiment=sentiment, meta=meta))
