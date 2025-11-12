from __future__ import annotations

from typing import Any, Dict

from .base import LLMProvider


class ClaudeSonnetProvider(LLMProvider):
    name = "claude_sonnet"

    async def complete(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # In production this would call the Anthropic API. For the reference implementation we
        # simulate a deterministic decision that mirrors the configured risk gates.
        sentiment = payload["sentiment"]
        features = payload["features"]
        verdict = "CONFIRM"
        tags: list[str] = []
        size_multiplier = 1.0
        if sentiment["event_severity"] == "high" or sentiment["sentiment_score"] < 0:
            verdict = "DOWNGRADE"
            tags.append("news_risk")
            size_multiplier = 0.5
        if features["atr_pct"] >= 0.8:
            verdict = "BLOCK"
            tags.append("volatility_spike")
            size_multiplier = 0.0
        return {
            "verdict": verdict,
            "size_multiplier": size_multiplier,
            "risk_tags": tags,
            "short_reason": "deterministic stub decision",
            "prompt_version": "v2.2.0",
            "cache_hit": False,
            "latency_ms": 0,
            "is_fallback": False,
            "stale_correlation": payload.get("stale_correlation", False),
        }
