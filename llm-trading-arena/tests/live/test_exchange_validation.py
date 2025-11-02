from __future__ import annotations

import asyncio
from typing import Any

import pytest

from src.adapters.exchange.binance_spot import BinanceSpotAdapter


class DummyResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self.status_code = 200

    def json(self) -> dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        return None


class DummyClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls = 0

    async def get(self, path: str) -> DummyResponse:
        self.calls += 1
        if path == "/api/v3/exchangeInfo":
            return DummyResponse(self.payload)
        raise AssertionError(path)


def test_exchange_info_cache() -> None:
    async def scenario() -> None:
        adapter = BinanceSpotAdapter({"base_url": "https://example.com", "recv_window_ms": 5000, "precision_cache_ttl_sec": 600})
        client = DummyClient({"symbols": []})
        adapter._http = client  # type: ignore[assignment]
        info = await adapter.get_exchange_info()
        assert info == {"symbols": []}
        info2 = await adapter.get_exchange_info()
        assert info2 == info
        assert client.calls == 1

    asyncio.run(scenario())
