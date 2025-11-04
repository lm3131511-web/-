from __future__ import annotations

import os
from typing import Any, Dict

from src.vendor import httpx

from .base import LLMProvider


class ClaudeProvider(LLMProvider):
    def __init__(self) -> None:
        super().__init__(name="claude")
        self._reliability = 0.7

    async def _raw_complete(self, *, prompt: str, schema: Dict[str, Any]) -> str:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY missing")
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": "claude-3-sonnet-20240229",
            "max_output_tokens": 800,
            "temperature": 0.2,
            "system": "You are a cautious trading analyst.",
            "messages": [{"role": "user", "content": prompt}],
        }
        async with httpx.AsyncClient(timeout=self.request_timeout) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages", headers=headers, json=payload
            )
            response.raise_for_status()
        data = response.json()
        usage = data.get("usage", {})
        prompt_tokens = int(usage.get("input_tokens", 0))
        completion_tokens = int(usage.get("output_tokens", 0))
        if prompt_tokens or completion_tokens:
            self._last_meta.update(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=(prompt_tokens + completion_tokens) / 1000.0 * 0.004,
            )
        content = data.get("content")
        if not content:
            raise RuntimeError("claude: missing content")
        if isinstance(content, list):
            text_chunks = [chunk.get("text", "") for chunk in content if isinstance(chunk, dict)]
            text = "\n".join(part for part in text_chunks if part)
        else:
            text = str(content)
        if not text:
            raise RuntimeError("claude: empty message")
        return text

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
            "reasoning": "stub-mode claude synthesis",
        }
