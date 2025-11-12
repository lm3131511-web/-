from __future__ import annotations

from typing import Dict, Tuple


def detect_regime(snapshot: Dict[str, float]) -> Tuple[str, float]:
    volatility = snapshot.get("volatility", 0.01)
    spread_bps = snapshot.get("spread_bps", 5.0)
    depth = snapshot.get("top_depth_usd", 1_000_000.0)
    if volatility > 0.06 or spread_bps > 15:
        return "volatile", min(1.0, 0.8 + volatility)
    if depth < 500_000:
        return "illiquid", 0.7
    if volatility < 0.02 and spread_bps < 5:
        return "stable_trend", 0.2
    return "chop", 0.4
