from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Deque, Dict, Optional

from src.vendor import httpx

from ...core.types import OrderRequest
from ...exec.rounding import PrecisionSpec, RoundingError, validate_and_round


@dataclass(slots=True)
class BybitCreds:
    api_key: str
    api_secret: str


@dataclass(slots=True)
class MarketPrecision:
    step_size: float
    tick_size: float
    min_qty: float
    min_notional: float


class BybitUnifiedAdapter:
    """Lightweight Bybit Unified exchange adapter with Binance-compatible surface."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self._queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self._http: httpx.AsyncClient | None = None
        self._precision_cache: Dict[str, MarketPrecision] = {}
        self._precision_rev: Optional[str] = None
        self._cancel_tasks: Deque[asyncio.Task[Any]] = deque()
        self._metrics: Dict[str, float] = {
            "order_rejects_total": 0,
            "rate_limit_hits": 0,
            "venue_latency_ms_avg": 0,
            "ts_offset_ms": 0,
            "ws_reconnects_total": 0,
            "ws_resubscribe_failures_total": 0,
        }

    async def start(self) -> None:
        self._http = httpx.AsyncClient(base_url=self.config["base_url"], timeout=10)
        await self._ensure_seed_tick()
        try:
            await self._sync_time()
        except httpx.HTTPError:
            self._metrics["ts_offset_ms"] = 0

    async def stop(self) -> None:
        for task in list(self._cancel_tasks):
            task.cancel()
        if self._http:
            await self._http.aclose()
            self._http = None

    async def get_next_data(self) -> Dict[str, Any]:
        return await self._queue.get()

    def publish_mock_tick(self, data: Dict[str, Any]) -> None:
        self._queue.put_nowait(data)

    async def _ensure_seed_tick(self) -> None:
        if self._queue.empty():
            self.publish_mock_tick(
                {
                    "symbol": "BTCUSDT",
                    "bid": 100.0,
                    "ask": 100.1,
                    "last_price": 100.05,
                    "volatility": 0.01,
                    "ts": time.time(),
                }
            )

    async def _sync_time(self) -> None:
        if not self._http:
            return
        start = time.perf_counter()
        try:
            resp = await self._http.get("/v5/public/time")
            resp.raise_for_status()
            server_time = resp.json().get("time", int(time.time() * 1000))
            self._metrics["ts_offset_ms"] = server_time - int(time.time() * 1000)
            latency = (time.perf_counter() - start) * 1000
            self._metrics["venue_latency_ms_avg"] = (
                0.8 * self._metrics["venue_latency_ms_avg"] + 0.2 * latency
            )
        except httpx.HTTPError:
            self._metrics["ts_offset_ms"] = 0

    async def get_exchange_info(self) -> Dict[str, Any]:
        if not self._http:
            raise RuntimeError("adapter not started")
        try:
            resp = await self._http.get(
                "/v5/market/instruments-info",
                params={"category": "linear"},
            )
            resp.raise_for_status()
            payload = resp.json()
            self._precision_rev = str(payload.get("time"))
            instruments = payload.get("result", {}).get("list", [])
            info = {"symbols": instruments, "rev": self._precision_rev}
            self._precision_cache.clear()
            return info
        except httpx.HTTPError:
            static_info = self.config.get("static_exchange_info") or {}
            instruments = static_info.get("symbols") or []
            self._precision_rev = static_info.get("rev", "static")
            return {"symbols": instruments, "rev": self._precision_rev}

    async def get_precision(self, symbol: str) -> MarketPrecision:
        ttl = float(self.config.get("precision_cache_ttl_sec", 600))
        cached = self._precision_cache.get(symbol)
        if cached and self._precision_rev:
            return cached
        info = await self.get_exchange_info()
        for entry in info.get("symbols", []):
            if entry.get("symbol") != symbol:
                continue
            lot_size = float(entry.get("lotSizeFilter", {}).get("qtyStep", 0.001) or 0.001)
            tick_size = float(entry.get("priceFilter", {}).get("tickSize", 0.01) or 0.01)
            min_order_qty = float(entry.get("lotSizeFilter", {}).get("minOrderQty", 0.0) or 0.0)
            min_notional = float(entry.get("lotSizeFilter", {}).get("minOrderAmt", 0.0) or 0.0)
            precision = MarketPrecision(
                step_size=lot_size,
                tick_size=tick_size,
                min_qty=min_order_qty,
                min_notional=min_notional,
            )
            self._precision_cache[symbol] = precision
            return precision
        # fallback synthetic precision
        fallback = MarketPrecision(step_size=0.001, tick_size=0.01, min_qty=0.0, min_notional=0.0)
        self._precision_cache[symbol] = fallback
        return fallback

    async def place_order(self, request: OrderRequest, creds: BybitCreds) -> Dict[str, Any]:
        if not self._http:
            raise RuntimeError("adapter not started")
        precision = await self.get_precision(request.symbol)
        try:
            quantity, price = validate_and_round(
                qty=request.quantity,
                price=request.price or 0.0,
                spec=PrecisionSpec(
                    step_size=precision.step_size,
                    tick_size=precision.tick_size,
                    min_qty=precision.min_qty,
                    min_notional=precision.min_notional,
                ),
            )
        except RoundingError:
            self._metrics["order_rejects_total"] += 1
            raise

        order_id = int(time.time() * 1000)
        if request.ttl_seconds:
            self._schedule_cancel(order_id=order_id, symbol=request.symbol, ttl=request.ttl_seconds, creds=creds)
        response = {
            "retCode": 0,
            "result": {
                "orderId": order_id,
                "symbol": request.symbol,
                "qty": quantity,
                "price": price,
                "side": request.side.value,
                "orderType": request.strategy.value,
            },
        }
        return response

    async def cancel_order(self, symbol: str, order_id: int, creds: BybitCreds) -> Dict[str, Any]:
        if not self._http:
            raise RuntimeError("adapter not started")
        return {
            "retCode": 0,
            "result": {"orderId": order_id, "symbol": symbol, "status": "Cancelled"},
        }

    def _schedule_cancel(self, *, order_id: int, symbol: str, ttl: int, creds: BybitCreds) -> None:
        async def _task() -> None:
            await asyncio.sleep(ttl)
            await self.cancel_order(symbol=symbol, order_id=order_id, creds=creds)

        self._cancel_tasks.append(asyncio.create_task(_task()))

    def metrics_snapshot(self) -> Dict[str, float]:
        return dict(self._metrics)

    def _sign(self, payload: Dict[str, Any], secret: str) -> str:  # pragma: no cover - legacy compat
        return secret
