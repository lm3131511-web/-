from __future__ import annotations

import asyncio
import time

import pytest

from src.adapters.exchange.binance_spot import BinanceSpotAdapter


class FakeResponse:
    def __init__(self, server_time: int) -> None:
        self._server_time = server_time
        self.status_code = 200

    def json(self) -> dict[str, int]:
        return {"serverTime": self._server_time}

    def raise_for_status(self) -> None:
        return None


class FakeClient:
    def __init__(self, server_time: int) -> None:
        self.server_time = server_time

    async def get(self, path: str) -> FakeResponse:
        assert path == "/api/v3/time"
        return FakeResponse(self.server_time)


def test_time_sync() -> None:
    async def scenario() -> None:
        adapter = BinanceSpotAdapter({"base_url": "https://example.com", "recv_window_ms": 5000, "precision_cache_ttl_sec": 1})
        now_ms = int(time.time() * 1000)
        adapter._http = FakeClient(now_ms + 500)  # type: ignore[assignment]
        await adapter._sync_time()
        assert abs(adapter.metrics_snapshot()["ts_offset_ms"] - 500) < 5

    asyncio.run(scenario())
