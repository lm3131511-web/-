from __future__ import annotations

import os
from typing import Any, Dict

from src.vendor import httpx

from .base import LLMProvider


class DeepSeekProvider(LLMProvider):
    def __init__(self) -> None:
        super().__init__(name="deepseek")
        self._reliability = 0.55

    async def _raw_complete(self, *, prompt: str, schema: Dict[str, Any]) -> str:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY missing")
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "max_tokens": schema.get("properties", {}).get("strategy", {}).get("maxLength", 800),
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self.request_timeout) as client:
            response = await client.post(
                "https://api.deepseek.com/chat/completions", json=payload, headers=headers
            )
            response.raise_for_status()
        data = response.json()
        usage = data.get("usage", {})
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))
        cost_usd = float(usage.get("total_cost", 0.0) or 0.0)
        if prompt_tokens or completion_tokens:
            self._last_meta.update(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=cost_usd or ((prompt_tokens + completion_tokens) / 1000.0 * 0.002),
            )
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("deepseek: empty choices")
        message = choices[0].get("message", {})
        content = message.get("content")
        if not content:
            raise RuntimeError("deepseek: missing content")
        return content

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
        micro_delta = float(vars_block.get("micro_price_delta", 0.0))

        direction = "FLAT"
        strategy = "POST_ONLY"
        urgency = min(1.0, max(0.2, abs(micro_delta) * 6 + risk_level * 0.3))

        if regime == "stable_trend":
            direction = "BUY" if micro_delta >= 0 else "SELL"
            strategy = "TWAP"
        elif regime == "volatile":
            if abs(imbalance) > 0.25 and spread < 15:
                direction = "BUY" if imbalance > 0 else "SELL"
            strategy = "IOC"
            urgency = max(urgency, 0.6)
        elif regime == "illiquid":
            strategy = "IOC"
            urgency = min(urgency, 0.5)
            if spread > 25 or depth < 500_000:
                direction = "FLAT"
        elif regime == "chop":
            if abs(imbalance) > 0.35:
                direction = "BUY" if imbalance > 0 else "SELL"
            strategy = "POST_ONLY"

        confidence = max(0.2, min(0.8, 0.45 + abs(imbalance) * 0.4 - risk_level * 0.3))
        size_hint = max(0.02, min(0.25, depth / 12_000_000 * (1 - risk_level)))
        ttl_span = max(ttl_max - ttl_min, 1)
        ttl_hint = ttl_max - int(ttl_span * min(1.0, urgency))
        price_band = max(1.0, min(spread, spread * 0.8))

        return {
            "direction": direction,
            "strategy": strategy,
            "confidence": confidence,
            "urgency": urgency,
            "size_hint_frac": size_hint,
            "ttl_hint_sec": max(ttl_min, min(ttl_max, ttl_hint)),
            "price_band_bps": price_band,
            "uncertainty_hints": [f"regime={regime}", f"spread={spread:.2f}bps"],
            "reliability": self._reliability,
            "requested_features": ["depth_snapshot", "recent_trades"],
        }
