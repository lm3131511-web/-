from __future__ import annotations


def calibrate_probability(raw_p: float, tau: float) -> float:
    clipped = min(1.0, max(0.0, raw_p))
    return (clipped + tau) / (1 + tau)
