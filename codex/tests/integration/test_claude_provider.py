import asyncio
import json

import httpx

from codex.llm_risk.providers.claude_sonnet import ClaudeSonnetProvider
from codex.config.models import Settings

def test_claude_provider_parses_json(monkeypatch, settings: Settings):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    provider = ClaudeSonnetProvider(
        settings,
        system_prompt="SYSTEM",
        client_factory=lambda: httpx.AsyncClient(transport=_mock_transport(_handler(settings))),
    )
    payload = {
        "features": {"regime": "normal", "rsi_14": 55, "atr_pct": 0.25, "spread_bps": 1.2},
        "sentiment": {"sentiment_score": 0.05, "event_severity": "low", "confidence": 0.3, "sources_confirmed": 1},
        "meta": {},
        "prompt_version": settings.prompt_version,
        "stale_correlation": False,
    }
    result = asyncio.run(provider.complete(payload))
    assert result["verdict"] == "CONFIRM"
    assert result["risk_tags"] == []


def _mock_transport(handler):
    return httpx.MockTransport(handler)


def _handler(settings: Settings):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/v1/messages")
        assert request.headers["anthropic-version"] == settings.get_llm_provider("claude").api_version
        body = json.loads(request.content)
        assert body["model"] == settings.get_llm_provider("claude").model
        response = {
            "verdict": "CONFIRM",
            "size_multiplier": 1.0,
            "risk_tags": [],
            "short_reason": "claude ok",
            "prompt_version": settings.prompt_version,
            "cache_hit": False,
            "latency_ms": 0,
            "is_fallback": False,
            "stale_correlation": False,
        }
        return httpx.Response(
            200,
            json={
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(response),
                    }
                ]
            },
        )

    return handler
