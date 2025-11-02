from __future__ import annotations

import asyncio
from typing import Any

import pytest

from src.adapters.exchange.binance_spot import BinanceSpotAdapter


def test_schedule_cancel_invokes_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    async def scenario() -> None:
        adapter = BinanceSpotAdapter(
            {
                "base_url": "https://example.com",
                "recv_window_ms": 5000,
                "precision_cache_ttl_sec": 600,
            }
        )
        called: dict[str, Any] = {}

        async def fake_cancel(symbol: str, order_id: int, creds: Any) -> None:
            called["symbol"] = symbol
            called["order_id"] = order_id

        monkeypatch.setattr(adapter, "cancel_order", fake_cancel)  # type: ignore[arg-type]
        adapter._schedule_cancel(symbol="BTCUSDT", order_id=1, ttl=0, creds=None)  # type: ignore[arg-type]
        await asyncio.sleep(0.01)
        assert called["symbol"] == "BTCUSDT"
        assert called["order_id"] == 1

    asyncio.run(scenario())
