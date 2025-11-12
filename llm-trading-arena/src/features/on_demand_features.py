from __future__ import annotations

from typing import Dict


def build_on_demand_features(tick: Dict[str, float], limit: int) -> Dict[str, float]:
    items = list(tick.items())[:limit]
    return {f"od_{k}": v for k, v in items}
