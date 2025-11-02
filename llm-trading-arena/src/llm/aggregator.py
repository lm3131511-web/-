from __future__ import annotations

import math
from typing import Iterable, List

from ..core.contracts import (
    AggregationContributor,
    AggregationResult,
    AnalystResponse,
)


class AggregationError(RuntimeError):
    """Raised when aggregation cannot deliver a decision."""


def _clamp(value: float, *, eps: float = 1e-6) -> float:
    return min(1.0 - eps, max(eps, value))


def _direction_to_probability(response: AnalystResponse) -> float:
    base = response.confidence
    if response.direction == "BUY":
        return base
    if response.direction == "SELL":
        return 1.0 - base
    return 0.5


def _compute_uncertainty(probabilities: List[float]) -> float:
    if not probabilities:
        return 1.0
    mean = sum(probabilities) / len(probabilities)
    variance = sum((p - mean) ** 2 for p in probabilities) / len(probabilities)
    uniform = 0.5
    m = 0.5 * (uniform + mean)
    kl_uniform = uniform * math.log(_clamp(uniform) / _clamp(m)) + (1 - uniform) * math.log(
        _clamp(1 - uniform) / _clamp(1 - m)
    )
    kl_mean = mean * math.log(_clamp(mean) / _clamp(m)) + (1 - mean) * math.log(
        _clamp(1 - mean) / _clamp(1 - m)
    )
    jsd = 0.5 * (kl_uniform + kl_mean)
    max_p = max(probabilities)
    uncertainty = 0.5 * min(1.0, variance * 4) + 0.3 * min(1.0, jsd / math.log(2)) + 0.2 * (1 - max_p)
    return max(0.0, min(1.0, uncertainty))


def _degradation_mode(uncertainty: float, budget_left: float, budget_total: float) -> str:
    budget_ratio = budget_left / budget_total if budget_total > 0 else 0.0
    if uncertainty >= 0.55 or budget_ratio <= 0.08:
        return "emergency"
    if uncertainty >= 0.45 or budget_ratio <= 0.15:
        return "minimal"
    if uncertainty >= 0.35 or budget_ratio <= 0.25:
        return "reduced"
    return "full"


def aggregate_responses(
    responses: Iterable[AnalystResponse],
    *,
    tau: float,
    budget_usd_per_min: float,
) -> AggregationResult:
    responses = list(responses)
    if not responses:
        raise AggregationError("no analyst responses")
    probabilities: List[float] = []
    weights: List[float] = []
    contributors: List[AggregationContributor] = []
    budget_spent = 0.0
    for response in responses:
        probability = _clamp(_direction_to_probability(response))
        prob_weight = math.exp(response.reliability * tau)
        probabilities.append(probability)
        weights.append(prob_weight)
        contributors.append(
            AggregationContributor(
                stage=response.stage,
                provider=response.provider,
                weight=prob_weight,
                reliability=response.reliability,
                probability=probability,
            )
        )
        token_cost = (response.prompt_tokens + response.completion_tokens) / 1000.0
        budget_spent += token_cost * 0.002  # synthetic blended price per token
    total_weight = sum(weights)
    if budget_spent > budget_usd_per_min and budget_usd_per_min > 0:
        raise AggregationError("budget exceeded")
    if total_weight <= 0:
        raise AggregationError("invalid analyst weights")
    normalized_weights = [w / total_weight for w in weights]
    logit_sum = 0.0
    for weight, probability in zip(normalized_weights, probabilities):
        logit_sum += weight * math.log(probability / (1.0 - probability))
    tau_used = max(0.0, tau)
    logit_final = tau_used * logit_sum
    p_final = 1.0 / (1.0 + math.exp(-logit_final))
    uncertainty = _compute_uncertainty(probabilities)
    budget_left = max(0.0, budget_usd_per_min - budget_spent)
    degradation_mode = _degradation_mode(uncertainty, budget_left, budget_usd_per_min)
    weight_map = {
        contributor.stage: weight for contributor, weight in zip(contributors, normalized_weights)
    }
    reliability_map = {contributor.stage: contributor.reliability for contributor in contributors}
    return AggregationResult(
        contributors=contributors,
        p_final=p_final,
        uncertainty=uncertainty,
        tau_used=tau_used,
        weights=weight_map,
        reliability_scores=reliability_map,
        budget_spent_usd=budget_spent,
        budget_left_usd=budget_left,
        degradation_mode=degradation_mode,
    )
