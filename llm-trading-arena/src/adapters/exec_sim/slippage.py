from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(slots=True)
class SlippageResult:
    executed_price: float
    slippage_bps: float
    stress_applied: bool


def _select_profile(economics: Dict[str, Any], stress: bool) -> Dict[str, float]:
    key = "stress" if stress else "normal"
    profile = economics.get(key, {})
    return {
        "k_vol_bps": float(profile.get("k_vol_bps", 0.35)),
        "sigma": float(profile.get("sigma", 0.6)),
    }


def simulate_slippage(
    *,
    side: str,
    mid_price: float,
    notional: float,
    spread_bps: float,
    volatility: float,
    depth_usd: float,
    economics: Dict[str, Any],
    rng: Optional[random.Random] = None,
) -> SlippageResult:
    """Return an execution price sampled from the configured slippage profile.

    The model is intentionally lightweight but incorporates:
    * probability of stress scenarios (`stress_slippage_prob`),
    * sensitivity to instantaneous spread / volatility,
    * depth-aware penalty for large notionals.
    """

    if rng is None:
        rng = random.Random()

    stress_prob = float(economics.get("stress_slippage_prob", 0.0))
    stress_applied = rng.random() < stress_prob
    profile = _select_profile(economics, stress_applied)

    mid_price = max(1e-8, float(mid_price))
    spread_bps = max(0.0, float(spread_bps))
    volatility = max(0.0, float(volatility))
    depth_usd = max(1.0, float(depth_usd))
    notional = max(0.0, float(notional))

    depth_ratio = min(1.0, notional / depth_usd)
    vol_component = profile["k_vol_bps"] * volatility * 10_000
    spread_component = spread_bps * 0.5
    noise = abs(rng.gauss(0.0, profile["sigma"])) * 10

    slippage_bps = spread_component + vol_component * (1 + depth_ratio) + noise
    if stress_applied:
        slippage_bps *= 1.5

    direction = 1 if side.upper() == "BUY" else -1
    executed_price = mid_price * (1 + direction * slippage_bps / 10_000)
    executed_price = max(1e-8, executed_price)

    return SlippageResult(
        executed_price=executed_price,
        slippage_bps=abs(slippage_bps),
        stress_applied=stress_applied,
    )
