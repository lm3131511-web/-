from __future__ import annotations


def compute_adv_fraction(p_final: float, uncertainty: float, max_fraction: float) -> float:
    base = p_final * (1 - uncertainty)
    return min(max_fraction, max(0.0, base))
