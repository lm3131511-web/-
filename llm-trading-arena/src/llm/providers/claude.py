from __future__ import annotations

from typing import Any, Dict

from .base import LLMProvider


class ClaudeProvider(LLMProvider):
    def __init__(self) -> None:
        super().__init__(name="claude")
        self._reliability = 0.72

    async def complete_json(
        self,
        *,
        prompt: str,
        schema: Dict[str, Any],
        market_snapshot: Dict[str, float],
    ) -> Dict[str, Any]:
        drift = market_snapshot.get("drift", 0.0)
        volatility = market_snapshot.get("volatility", 0.01)
        risk_state = market_snapshot.get("risk_state", 0.0)
        direction = "FLAT" if abs(risk_state) > 0.5 else ("BUY" if drift >= 0 else "SELL")
        base_conf = 0.58 + (0.2 - volatility * 5)
        confidence = max(0.5, min(0.92, base_conf))
        urgency = max(0.2, min(0.8, 0.3 + risk_state * 0.1 + volatility * 10))
        strategy = "TWAP" if direction == "FLAT" else "POST_ONLY"
        size_hint = 0.0 if direction == "FLAT" else min(0.2, 0.08 + abs(drift) * 2)
        ttl = 60
        return {
            "direction": direction,
            "strategy": strategy,
            "confidence": confidence,
            "urgency": urgency,
            "size_hint_frac": size_hint,
            "ttl_hint_sec": ttl,
            "price_band_bps": max(3.0, volatility * 8000),
            "uncertainty_hints": [f"risk_state={risk_state:.2f}"],
            "reliability": self._reliability,
            "reasoning": f"Claude consensus for {prompt}",
            "requested_features": ["best_bid_ask"],
        }
