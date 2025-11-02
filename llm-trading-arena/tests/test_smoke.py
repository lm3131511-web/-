from __future__ import annotations

import asyncio
import time

import pytest
from src.vendor import httpx

from src.adapters.exchange.binance_spot import BinanceSpotAdapter
from src.config.loader import load_config
from src.config.validators import validate_config
from src.monitoring.metrics import GLOBAL_METRICS


class _DummyResponse:
    def __init__(self, payload: dict[str, float | dict[str, object]]) -> None:
        self._payload = payload
        self.status_code = 200

    def json(self) -> dict[str, float | dict[str, object]]:
        return self._payload

    def raise_for_status(self) -> None:
        return None


class _DummyClient:
    def __init__(self, *args, **kwargs) -> None:
        self._closed = False

    async def get(self, path: str, *_, **__) -> _DummyResponse:
        if path == "/api/v3/time":
            return _DummyResponse({"serverTime": int(time.time() * 1000)})
        if path == "/api/v3/exchangeInfo":
            return _DummyResponse(
                {
                    "symbols": [
                        {
                            "symbol": "BTCUSDT",
                            "filters": [
                                {"filterType": "LOT_SIZE", "stepSize": "0.001", "minQty": "0.001"},
                                {"filterType": "PRICE_FILTER", "tickSize": "0.01"},
                                {"filterType": "MIN_NOTIONAL", "minNotional": "10"},
                            ],
                        }
                    ]
                }
            )
        raise AssertionError(f"unexpected path: {path}")

    async def post(self, *args, **kwargs):  # pragma: no cover - not used in smoke test
        raise AssertionError("post not expected")

    async def delete(self, *args, **kwargs):  # pragma: no cover - not used in smoke test
        raise AssertionError("delete not expected")

    async def aclose(self) -> None:
        self._closed = True


def test_smoke_config_and_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    config = load_config("config.sample.yaml")
    validate_config(config)

    async def scenario() -> None:
        monkeypatch.setattr(httpx, "AsyncClient", _DummyClient)

        adapter = BinanceSpotAdapter(config.exchange.model_dump())
        await adapter.start()
        try:
            metrics = adapter.metrics_snapshot()
            assert isinstance(metrics, dict)
            assert "ts_offset_ms" in metrics
            assert isinstance(GLOBAL_METRICS.snapshot(), dict)
        finally:
            await adapter.stop()

        tick = await asyncio.wait_for(adapter.get_next_data(), timeout=0.1)
        assert tick["symbol"] == "BTCUSDT"

    asyncio.run(scenario())
