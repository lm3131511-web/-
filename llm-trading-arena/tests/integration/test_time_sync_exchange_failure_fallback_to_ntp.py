import asyncio

from src.vendor import httpx

from src.adapters.exchange.bybit_unified import BybitUnifiedAdapter


class FailingClient:
    async def get(self, path):
        raise httpx.HTTPError("boom")


def test_time_sync_failure_sets_zero_offset() -> None:
    async def _run() -> None:
        adapter = BybitUnifiedAdapter(
            {"base_url": "https://api.bybit.com", "recv_window_ms": 5000, "precision_cache_ttl_sec": 1}
        )
        adapter._http = FailingClient()
        await adapter._sync_time()
        assert adapter.metrics_snapshot()["ts_offset_ms"] == 0

    asyncio.run(_run())
