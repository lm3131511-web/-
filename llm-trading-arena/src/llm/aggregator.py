from __future__ import annotations

from typing import Iterable, List

from ..core.contracts import AggregationContributor, AggregationResult, AnalystResponse


class AggregationError(RuntimeError):
    pass


def aggregate_responses(
    responses: Iterable[AnalystResponse],
    tau: float,
    max_budget_usd: float,
) -> AggregationResult:
    contributors: List[AggregationContributor] = []
    total_weight = 0.0
    weighted_p = 0.0
    budget_spent = 0.0
    for idx, response in enumerate(responses):
        weight = max(0.05, response.decision_confidence)
        contributors.append(
            AggregationContributor(stage=response.stage, weight=weight, p_hat=response.decision_confidence)
        )
        weighted_p += response.decision_confidence * weight
        total_weight += weight
        budget_spent += (response.prompt_tokens + response.completion_tokens) / 1000.0
    if total_weight == 0:
        raise AggregationError("no analyst responses")
    p_final = min(1.0, max(0.0, weighted_p / total_weight))
    uncertainty = max(0.0, min(1.0, 1.0 - min(total_weight / (len(contributors) * tau + 1e-6), 1.0)))
    if budget_spent > max_budget_usd:
        raise AggregationError("budget exceeded")
    return AggregationResult(
        contributors=contributors,
        p_final=p_final,
        uncertainty=uncertainty,
        tau=tau,
        budget_spent_usd=budget_spent,
    )
