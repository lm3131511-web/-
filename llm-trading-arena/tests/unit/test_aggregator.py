from __future__ import annotations

from src.core.contracts import AnalystResponse
from src.llm.aggregator import aggregate_responses


def make_response(stage: str, confidence: float, reliability: float, direction: str = "BUY") -> AnalystResponse:
    return AnalystResponse(
        stage=stage,
        provider=stage.lower(),
        prompt_tokens=120,
        completion_tokens=40,
        latency_ms=12.0,
        direction=direction,
        strategy="POST_ONLY",
        confidence=confidence,
        urgency=0.5,
        size_hint_frac=0.12,
        ttl_hint_sec=45,
        price_band_hint=None,
        uncertainty_hints=["synthetic"],
        requested_features=[],
        reliability=reliability,
        reasoning="test",
    )


def test_log_opinion_pool_weights_and_uncertainty() -> None:
    responses = [
        make_response("A", confidence=0.7, reliability=0.8, direction="BUY"),
        make_response("B", confidence=0.55, reliability=0.6, direction="SELL"),
        make_response("C", confidence=0.6, reliability=0.7, direction="BUY"),
    ]
    result = aggregate_responses(responses, tau=1.0, budget_usd_per_min=1.0)
    assert 0.0 <= result.p_final <= 1.0
    assert abs(sum(result.weights.values()) - 1.0) < 1e-6
    assert result.uncertainty < 1.0
    assert result.degradation_mode in {"full", "reduced", "minimal", "emergency"}
    assert result.budget_spent_usd > 0
