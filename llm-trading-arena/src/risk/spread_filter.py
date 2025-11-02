from __future__ import annotations

def calculate_spread_bps(*, bid: float, ask: float) -> float:
    mid = (bid + ask) / 2.0
    if mid <= 0:
        return 1e9
    return (ask - bid) / mid * 10_000.0
