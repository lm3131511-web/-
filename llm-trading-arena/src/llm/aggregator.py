from __future__ import annotations

import math
from typing import Iterable, List

from ..core.contracts import AggregationContributor, AggregationResult, AnalystResponse
from ..monitoring.metrics import GLOBAL_METRICS
from ..utils.time import now_utc_iso


class AggregationError(RuntimeError):
    """Raised when aggregation cannot produce a valid probability."""


def _clamp_probability(value: float) -> float:
    eps = 1e-6
    return min(1.0 - eps, max(eps, value))


def _direction_to_probability(response: AnalystResponse) -> float:
    if response.direction == "BUY":
        return response.confidence
    if response.direction == "SELL":
        return 1.0 - response.confidence
    return 0.5


def _uncertainty(probabilities: List[float]) -> float:
    if not probabilities:
        return 1.0
    mean = sum(probabilities) / len(probabilities)
    variance = sum((p - mean) ** 2 for p in probabilities) / len(probabilities)
    uniform = 0.5
    m = 0.5 * (uniform + mean)
    jsd = 0.0
    if 0.0 < m < 1.0:
        kl_uniform = uniform * math.log(_clamp_probability(uniform) / _clamp_probability(m)) + (
            1 - uniform
        ) * math.log(_clamp_probability(1 - uniform) / _clamp_probability(1 - m))
        kl_mean = mean * math.log(_clamp_probability(mean) / _clamp_probability(m)) + (1 - mean) * math.log(
            _clamp_probability(1 - mean) / _clamp_probability(1 - m)
        )
        jsd = 0.5 * (kl_uniform + kl_mean)
    max_p = max(probabilities)
    u = 0.5 * min(1.0, variance * 4) + 0.3 * min(1.0, jsd / math.log(2)) + 0.2 * (1 - max_p)
    return max(0.0, min(1.0, u))


def aggregate_responses(
    responses: Iterable[AnalystResponse],
    *,
    tau: float,
    reliability_lambda: float,
    budget_limit_usd: float,
    degradation_mode: str,
) -> AggregationResult:
    responses = list(responses)
    if not responses:
        raise AggregationError("no analyst responses available")

    weights: List[float] = []
    probabilities: List[float] = []
    contributors: List[AggregationContributor] = []
    budget_spent = 0.0
    for response in responses:
        probability = _clamp_probability(_direction_to_probability(response))
        weight = math.exp(reliability_lambda * response.reliability)
        weights.append(weight)
        probabilities.append(probability)
        contributors.append(
            AggregationContributor(
                stage=response.stage,
                provider=response.provider,
                weight=weight,
                reliability=response.reliability,
                probability=probability,
            )
        )
        token_cost = (response.prompt_tokens + response.completion_tokens) / 1000.0
        budget_spent += token_cost * 0.002  # synthetic blended price per token

    if budget_limit_usd > 0 and budget_spent > budget_limit_usd * 1.05:
        raise AggregationError("llm budget exceeded")

    total_weight = sum(weights)
    if total_weight <= 0:
        raise AggregationError("invalid analyst weights")

    normalized_weights = [w / total_weight for w in weights]
    logit = 0.0
    for probability, weight in zip(probabilities, normalized_weights):
        logit += weight * math.log(probability / (1.0 - probability))
    logit *= tau
    p_final = 1.0 / (1.0 + math.exp(-logit))
    uncertainty = _uncertainty(probabilities)
    budget_left = max(0.0, budget_limit_usd - budget_spent)
    weight_map = {
        contributor.stage: weight for contributor, weight in zip(contributors, normalized_weights)
    }
    reliability_map = {contributor.stage: contributor.reliability for contributor in contributors}
    GLOBAL_METRICS.record_weights(weight_map)
    return AggregationResult(
        contributors=contributors,
        p_final=p_final,
        uncertainty=uncertainty,
        tau_used=tau,
        weights=weight_map,
        reliability_scores=reliability_map,
        budget_spent_usd=budget_spent,
        budget_left_usd=budget_left,
        degradation_mode=degradation_mode,
        updated_at=now_utc_iso(),
    )
