import asyncio
import json

import httpx

from codex.llm_risk.providers.deepseek import DeepSeekProvider
from codex.config.models import Settings

def test_deepseek_provider_parses_json(monkeypatch, settings: Settings):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    provider = DeepSeekProvider(
        settings,
        system_prompt="SYSTEM",
        client_factory=lambda: httpx.AsyncClient(transport=_mock_transport(_handler(settings))),
    )
    payload = {
        "features": {"regime": "normal", "rsi_14": 50, "atr_pct": 0.2, "spread_bps": 1.5},
        "sentiment": {"sentiment_score": 0.0, "event_severity": "none", "confidence": 0.1, "sources_confirmed": 0},
        "meta": {},
        "prompt_version": settings.prompt_version,
        "stale_correlation": False,
    }
    result = asyncio.run(provider.complete(payload))
    assert result["verdict"] == "CONFIRM"
    assert result["is_fallback"] is False


def _mock_transport(handler):
    return httpx.MockTransport(handler)


def _handler(settings: Settings):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/chat/completions")
        body = json.loads(request.content)
        assert body["model"] == settings.get_llm_provider("deepseek").model
        response = {
            "verdict": "CONFIRM",
            "size_multiplier": 1.0,
            "risk_tags": [],
            "short_reason": "fallback idle",
            "prompt_version": settings.prompt_version,
            "cache_hit": False,
            "latency_ms": 0,
            "is_fallback": False,
            "stale_correlation": False,
        }
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(response),
                        }
                    }
                ]
            },
        )

    return handler
