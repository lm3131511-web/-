from __future__ import annotations

from typing import Any, Dict

from .base import LLMProvider


class LocalLlamaProvider(LLMProvider):
    name = "local_llama"

    async def complete(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "verdict": "DOWNGRADE",
            "size_multiplier": 0.6,
            "risk_tags": ["correlation_risk"] if payload.get("stale_correlation") else [],
            "short_reason": "local llama conservative decision",
            "prompt_version": "v2.2.0",
            "cache_hit": False,
            "latency_ms": 0,
            "is_fallback": True,
            "stale_correlation": payload.get("stale_correlation", False),
        }
