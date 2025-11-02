from __future__ import annotations

from typing import Dict


def build_core_features(tick: Dict[str, float]) -> Dict[str, float]:
    return {f"core_{k}": v for k, v in tick.items()}
