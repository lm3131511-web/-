from __future__ import annotations


def compute_final_fraction(
    *,
    size_hint_frac: float,
    kelly_base: float,
    safety_multiplier: float,
    max_cap: float,
) -> float:
    """Blend LLM hints with Kelly sizing under a hard cap."""

    base = max(0.0, kelly_base * safety_multiplier)
    hinted = max(size_hint_frac, base)
    return min(max_cap, hinted)
