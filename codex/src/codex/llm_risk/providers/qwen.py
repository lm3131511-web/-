from __future__ import annotations

from typing import Any, Dict

from .base import LLMProvider


class QwenProvider(LLMProvider):
    name = "qwen"

    async def complete(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "verdict": "CONFIRM",
            "size_multiplier": 0.8,
            "risk_tags": [],
            "short_reason": "qwen fallback decision",
            "prompt_version": "v2.2.0",
            "cache_hit": False,
            "latency_ms": 0,
            "is_fallback": True,
            "stale_correlation": payload.get("stale_correlation", False),
        }
