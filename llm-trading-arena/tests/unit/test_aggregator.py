from __future__ import annotations

from src.core.contracts import AnalystResponse
from src.llm.aggregator import aggregate_responses


def make_response(stage: str, confidence: float) -> AnalystResponse:
    return AnalystResponse(
        stage=stage,
        prompt_tokens=100,
        completion_tokens=20,
        latency_ms=10.0,
        decision_confidence=confidence,
        recommended_action="BUY",
        reasoning="",
    )


def test_aggregate_responses_bounds() -> None:
    responses = [make_response("A", 0.8), make_response("B", 0.4)]
    result = aggregate_responses(responses, tau=1.0, max_budget_usd=10)
    assert 0.0 <= result.p_final <= 1.0
    assert result.budget_spent_usd > 0
