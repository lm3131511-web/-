from __future__ import annotations


def degrade_probability(p: float, uncertainty: float) -> float:
    return max(0.0, min(1.0, p * (1.0 - uncertainty)))
