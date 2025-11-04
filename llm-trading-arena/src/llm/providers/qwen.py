from __future__ import annotations

from typing import Dict

from .base import LLMProvider


class QwenProvider(LLMProvider):
    def __init__(self) -> None:
        super().__init__(name="qwen")
        self._reliability = 0.6

    async def _raw_complete(self, *, prompt: str, schema: Dict[str, Any]) -> str:
        raise RuntimeError("Qwen API not configured")

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
        if spread <= limits.get("max_spread_bps", 12) and depth > 1_500_000 and risk_level < 0.6:
            if regime in {"stable_trend", "volatile"} and abs(imbalance) > 0.15:
                direction = "BUY" if imbalance > 0 else "SELL"
                strategy = "IOC" if regime == "volatile" else "TWAP"
        if regime == "stable_trend" and direction != "FLAT" and spread < 8:
            strategy = "POV"

        urgency = max(0.2, min(0.9, 0.35 + (1 - risk_level) * 0.4 + abs(imbalance) * 0.3))
        ttl_target = ttl_min + int((ttl_max - ttl_min) * (1 - urgency))
        price_band = max(1.0, min(spread, spread * (0.6 if strategy == "POST_ONLY" else 0.85)))
        size_hint = max(0.01, min(0.2, 0.04 + depth / 15_000_000))
        if risk_level >= 0.6:
            size_hint = min(size_hint, 0.05)

        return {
            "direction": direction,
            "strategy": strategy,
            "confidence": max(0.25, min(0.7, 0.5 + abs(imbalance) * 0.3 - risk_level * 0.2)),
            "urgency": urgency,
            "size_hint_frac": size_hint,
            "ttl_hint_sec": max(ttl_min, min(ttl_max, ttl_target)),
            "price_band_bps": price_band,
            "uncertainty_hints": [f"regime={regime}", f"risk={risk_level:.2f}"],
            "reliability": self._reliability,
            "requested_features": ["spread_history"] if spread < 8 else [],
        }
