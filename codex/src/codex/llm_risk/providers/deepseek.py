from __future__ import annotations

from typing import Any, Dict

from .base import LLMProvider


class DeepSeekProvider(LLMProvider):
    name = "deepseek"

    async def complete(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "verdict": "DOWNGRADE",
            "size_multiplier": 0.3,
            "risk_tags": ["llm_fallback"],
            "short_reason": "fallback conservative decision",
            "prompt_version": "v2.2.0",
            "cache_hit": False,
            "latency_ms": 0,
            "is_fallback": True,
            "stale_correlation": payload.get("stale_correlation", False),
        }
