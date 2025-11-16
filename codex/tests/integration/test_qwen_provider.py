import asyncio
import json

import httpx

from codex.llm_risk.providers.qwen import QwenProvider
from codex.config.models import Settings

def test_qwen_provider_parses_json(monkeypatch, settings: Settings):
    monkeypatch.setenv("QWEN_API_KEY", "test-key")
    provider = QwenProvider(
        settings,
        system_prompt="SYSTEM",
        client_factory=lambda: httpx.AsyncClient(transport=_mock_transport(_qwen_handler(settings))),
    )
    payload = {
        "features": {"regime": "normal", "rsi_14": 45, "atr_pct": 0.3, "spread_bps": 2},
        "sentiment": {"sentiment_score": 0.1, "event_severity": "low", "confidence": 0.5, "sources_confirmed": 1},
        "meta": {},
        "prompt_version": settings.prompt_version,
        "stale_correlation": False,
    }
    result = asyncio.run(provider.complete(payload))
    assert result["verdict"] == "CONFIRM"
    assert result["cache_hit"] is False


def _mock_transport(handler):
    return httpx.MockTransport(handler)


def _qwen_handler(settings: Settings):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/chat/completions")
        body = json.loads(request.content)
        assert body["model"] == settings.get_llm_provider("qwen").model
        assert body["messages"][0]["content"].startswith("SYSTEM")
        response = {
            "verdict": "CONFIRM",
            "size_multiplier": 1.0,
            "risk_tags": [],
            "short_reason": "inputs benign",
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
