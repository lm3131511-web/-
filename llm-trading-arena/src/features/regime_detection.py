from __future__ import annotations

from typing import Dict


def detect_regime(tick: Dict[str, float]) -> str:
    volatility = tick.get("volatility", 0.0)
    if volatility > 0.05:
        return "high_vol"
    if volatility > 0.02:
        return "medium_vol"
    return "calm"
