import asyncio
import time
from types import SimpleNamespace

from src.adapters.exchange.binance_spot import BinanceSpotAdapter


def test_precision_cache_invalidation_updates_metric() -> None:
    async def _run() -> None:
        adapter = BinanceSpotAdapter(
            {
                "base_url": "https://api.binance.com",
                "recv_window_ms": 5000,
                "precision_cache_ttl_sec": 1,
            }
        )

        payload = {
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

        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict:
                return payload

        async def fake_get(path):
            return FakeResponse()

        adapter._http = SimpleNamespace(get=fake_get)
        await adapter.get_precision("BTCUSDT")
        assert adapter._metrics["precision_cache_invalidations_total"] == 0
        adapter._exchange_info_ts -= 10
        await adapter.get_precision("BTCUSDT")
        assert adapter._metrics["precision_cache_invalidations_total"] == 1

    asyncio.run(_run())
