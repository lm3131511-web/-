from __future__ import annotations

from typing import Dict

from .base import LLMProvider


class ClaudeProvider(LLMProvider):
    def __init__(self) -> None:
        super().__init__(name="claude")
        self._reliability = 0.7

    async def _raw_complete(self, *, prompt: str, schema: Dict[str, Any]) -> str:
        raise RuntimeError("Claude API not configured")

    def _mock_completion(self, *, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        vars_block = self._extract_vars(prompt)
        limits = vars_block.get("limits", {})
        ttl_bounds = limits.get("ttl_sec_range", [30, 120])
        ttl_min, ttl_max = int(ttl_bounds[0]), int(ttl_bounds[-1])
        regime = str(vars_block.get("regime", "chop"))
        risk_level = float(vars_block.get("risk_level", 0.5))
        spread = float(vars_block.get("spread_bps", 10.0))
        depth = float(vars_block.get("depth_usd_top", 1_000_000.0))
        imbalance = float(vars_block.get("imbalance", 0.0))

        direction = "FLAT"
        strategy = "POST_ONLY"
        if regime == "stable_trend" and risk_level < 0.5 and abs(imbalance) > 0.2:
            direction = "BUY" if imbalance > 0 else "SELL"
            strategy = "TWAP"
        elif regime == "volatile":
            strategy = "IOC"
        elif regime == "illiquid":
            strategy = "IOC"
            if spread > 18 or depth < 600_000:
                direction = "FLAT"

        urgency = max(0.1, min(0.8, 0.25 + risk_level * 0.3 + (abs(imbalance) * 0.2)))
        if direction == "FLAT":
            urgency = min(urgency, 0.4)
        ttl_target = ttl_max if direction == "FLAT" else ttl_min + int((ttl_max - ttl_min) * 0.7)
        if regime == "volatile":
            ttl_target = max(ttl_min, int(ttl_min + (ttl_max - ttl_min) * 0.2))

        price_band = max(1.0, min(spread, spread * 0.7))
        size_cap = 0.18 if depth > 2_000_000 else 0.1
        size_hint = 0.0 if direction == "FLAT" else min(size_cap, 0.06 + depth / 20_000_000)

        return {
            "direction": direction,
            "strategy": strategy,
            "confidence": max(0.2, min(0.65, 0.45 + abs(imbalance) * 0.3 - risk_level * 0.3)),
            "urgency": urgency,
            "size_hint_frac": size_hint,
            "ttl_hint_sec": max(ttl_min, min(ttl_max, ttl_target)),
            "price_band_bps": price_band,
            "uncertainty_hints": [f"regime={regime}", f"risk={risk_level:.2f}"],
            "reliability": self._reliability,
            "requested_features": ["top_of_book"],
        }
