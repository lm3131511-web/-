from __future__ import annotations

from typing import Any, Dict

from .base import LLMProvider


class QwenProvider(LLMProvider):
    def __init__(self) -> None:
        super().__init__(name="qwen")
        self._reliability = 0.65

    async def complete_json(
        self,
        *,
        prompt: str,
        schema: Dict[str, Any],
        market_snapshot: Dict[str, float],
    ) -> Dict[str, Any]:
        spread_bps = market_snapshot.get("spread_bps", 8.0)
        volatility = market_snapshot.get("volatility", 0.01)
        bias = -0.02 if spread_bps > 12 else 0.02
        signal = market_snapshot.get("micro_price_delta", 0.0) + bias
        direction = "BUY" if signal >= 0 else "SELL"
        confidence = min(0.9, 0.6 + abs(signal) * 8)
        urgency = min(1.0, 0.4 + spread_bps / 50)
        strategy = "POST_ONLY" if spread_bps >= 6 else "IOC"
        size_hint = min(0.25, 0.1 + abs(signal) * 4)
        ttl = int(45 + (volatility * -500))
        return {
            "direction": direction,
            "strategy": strategy,
            "confidence": confidence,
            "urgency": urgency,
            "size_hint_frac": size_hint,
            "ttl_hint_sec": max(20, ttl),
            "price_band_bps": max(4.0, spread_bps * 0.8),
            "uncertainty_hints": [f"spread={spread_bps:.2f}bps"],
            "reliability": self._reliability,
            "reasoning": f"Qwen synthesised prompt={prompt}",
            "requested_features": ["micro_trades"],
        }
