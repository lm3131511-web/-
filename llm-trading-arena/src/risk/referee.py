from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from ..core.contracts import AnalystResponse, RefereeVerdict, Signal


@dataclass
class RefereeLimits:
    ttl_range: tuple[int, int]
    allowed_strategies: Iterable[str]


class Referee:
    """Lightweight validator ensuring LLM directives stay within safe bounds."""

    def __init__(self, *, limits: RefereeLimits) -> None:
        self.limits = limits

    def evaluate(self, response: AnalystResponse, signal: Signal) -> RefereeVerdict:
        issues: List[str] = []
        if response.confidence < 0 or response.confidence > 1:
            issues.append("confidence_range_violation")
        if response.urgency < 0 or response.urgency > 1:
            issues.append("urgency_range_violation")
        if response.size_hint_frac < 0:
            issues.append("size_hint_negative")
        if response.price_band_hint and response.price_band_hint.width_bps < 0:
            issues.append("price_band_negative")
        if response.ttl_hint_sec is not None:
            low, high = self.limits.ttl_range
            if response.ttl_hint_sec < low or response.ttl_hint_sec > high:
                issues.append("ttl_out_of_bounds")
        if response.strategy not in set(self.limits.allowed_strategies):
            issues.append("strategy_not_enabled")
        if signal.strategy != response.strategy:
            issues.append("strategy_mismatch")
        feasible = not issues
        adjusted_confidence = None
        if response.confidence > 1:
            adjusted_confidence = 1.0
        elif response.confidence < 0:
            adjusted_confidence = 0.0
        return RefereeVerdict(feasible=feasible, issues=issues, adjusted_confidence=adjusted_confidence)
