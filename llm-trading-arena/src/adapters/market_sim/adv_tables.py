from __future__ import annotations

from typing import Dict


def adv_share(symbol: str, adv_table: Dict[str, float], fraction: float) -> float:
    adv = adv_table.get(symbol, 0.0)
    return adv * fraction
