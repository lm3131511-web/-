import asyncio
from types import MethodType, SimpleNamespace

import asyncio

import pytest
from src.vendor import httpx

from src.adapters.exchange.binance_spot import BinanceCreds, BinanceSpotAdapter
from src.core.types import ExecutionStrategy, OrderRequest, OrderSide


class DummyResponse:
    status_code = 429
    is_client_error = True

    def json(self) -> dict:
        return {}

    def raise_for_status(self) -> None:
        raise httpx.HTTPError("rate limit")


def test_rate_limit_increments_metric() -> None:
    async def _run() -> None:
        adapter = BinanceSpotAdapter(
            {"base_url": "https://api.binance.com", "recv_window_ms": 5000, "precision_cache_ttl_sec": 1}
        )

        async def fake_exchange_info(self):
            return {
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

        adapter.get_exchange_info = MethodType(fake_exchange_info, adapter)

        async def fake_post(path, data=None, headers=None):
            return DummyResponse()

        adapter._http = SimpleNamespace(post=fake_post)
        request = OrderRequest(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            strategy=ExecutionStrategy.POST_ONLY,
            quantity=0.01,
            price=1000.0,
            ttl_seconds=30,
            client_order_id="arena-test",
        )
        creds = BinanceCreds(api_key="key", api_secret="secret")
        with pytest.raises(httpx.HTTPError):
            await adapter.place_order(request, creds)
        metrics = adapter.metrics_snapshot()
        assert metrics["rate_limit_hits"] == 1

    asyncio.run(_run())
