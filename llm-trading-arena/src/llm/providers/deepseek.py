from __future__ import annotations

from typing import Any, Dict

from .base import LLMProvider


class DeepSeekProvider(LLMProvider):
    def __init__(self) -> None:
        super().__init__(name="deepseek")
        self._reliability = 0.55

    async def complete_json(
        self,
        *,
        prompt: str,
        schema: Dict[str, Any],
        market_snapshot: Dict[str, float],
    ) -> Dict[str, Any]:
        drift = market_snapshot.get("drift", 0.0)
        volatility = market_snapshot.get("volatility", 0.01)
        direction = "BUY" if drift >= 0 else "SELL"
        confidence = min(0.85, 0.55 + abs(drift) * 5)
        urgency = min(1.0, 0.5 + volatility * 20)
        strategy = "POV" if abs(drift) < 0.03 else "IOC"
        size_hint = min(0.3, 0.12 + abs(drift) * 3)
        ttl = int(max(15, 120 - volatility * 1000))
        return {
            "direction": direction,
            "strategy": strategy,
            "confidence": confidence,
            "urgency": urgency,
            "size_hint_frac": size_hint,
            "ttl_hint_sec": ttl,
            "price_band_bps": max(5.0, volatility * 10000),
            "uncertainty_hints": [f"volatility={volatility:.4f}", f"drift={drift:.4f}"],
            "reliability": self._reliability,
            "reasoning": f"DeepSeek analysed prompt={prompt}",
            "requested_features": ["book_top", "recent_trades"],
        }
