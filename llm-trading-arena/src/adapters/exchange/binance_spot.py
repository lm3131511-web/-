from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Deque, Dict

from src.vendor import httpx

from ...core.types import OrderRequest
from ...exec.rounding import PrecisionSpec, RoundingError, validate_and_round


@dataclass(slots=True)
class BinanceCreds:
    api_key: str
    api_secret: str


@dataclass(slots=True)
class MarketPrecision:
    step_size: float
    tick_size: float
    min_qty: float
    min_notional: float


class BinanceSpotAdapter:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self._queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self._http: httpx.AsyncClient | None = None
        self._exchange_info: Dict[str, Any] | None = None
        self._exchange_info_ts: float = 0.0
        self._time_offset_ms: float = 0.0
        self._tasks: set[asyncio.Task[Any]] = set()
        self._cancel_tasks: Deque[asyncio.Task[Any]] = deque()
        self._precision_cache: Dict[str, MarketPrecision] = {}
        self._metrics: Dict[str, float] = {
            "order_rejects_total": 0,
            "rate_limit_hits": 0,
            "venue_latency_ms_avg": 0,
            "ts_offset_ms": 0,
        }

    async def start(self) -> None:
        self._http = httpx.AsyncClient(base_url=self.config["base_url"], timeout=10)
        try:
            await self._sync_time()
        except httpx.HTTPError:
            self._metrics["ts_offset_ms"] = 0.0
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

    async def stop(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        for task in list(self._cancel_tasks):
            task.cancel()
        if self._http:
            await self._http.aclose()
            self._http = None

    async def get_next_data(self) -> Dict[str, Any]:
        return await self._queue.get()

    def publish_mock_tick(self, data: Dict[str, Any]) -> None:
        self._queue.put_nowait(data)

    async def _sync_time(self) -> None:
        if not self._http:
            return
        start = time.perf_counter()
        resp = await self._http.get("/api/v3/time")
        resp.raise_for_status()
        server_time = resp.json()["serverTime"]
        self._time_offset_ms = server_time - int(time.time() * 1000)
        self._metrics["ts_offset_ms"] = self._time_offset_ms
        latency = (time.perf_counter() - start) * 1000
        self._metrics["venue_latency_ms_avg"] = (
            self._metrics["venue_latency_ms_avg"] * 0.8 + latency * 0.2
        )

    async def get_exchange_info(self) -> Dict[str, Any]:
        ttl = float(self.config.get("precision_cache_ttl_sec", 600))
        if self._exchange_info and (time.time() - self._exchange_info_ts) < ttl:
            return self._exchange_info
        if not self._http:
            raise RuntimeError("adapter not started")
        resp = await self._http.get("/api/v3/exchangeInfo")
        resp.raise_for_status()
        self._exchange_info = resp.json()
        self._exchange_info_ts = time.time()
        self._precision_cache.clear()
        return self._exchange_info

    async def get_precision(self, symbol: str) -> MarketPrecision:
        ttl = float(self.config.get("precision_cache_ttl_sec", 600))
        if symbol in self._precision_cache and (time.time() - self._exchange_info_ts) < ttl:
            return self._precision_cache[symbol]
        info = await self.get_exchange_info()
        for entry in info.get("symbols", []):
            if entry.get("symbol") != symbol:
                continue
            filters = {f["filterType"]: f for f in entry.get("filters", [])}
            lot = filters.get("LOT_SIZE") or {}
            price = filters.get("PRICE_FILTER") or {}
            notional = filters.get("MIN_NOTIONAL") or {}
            precision = MarketPrecision(
                step_size=float(lot.get("stepSize", 1.0)),
                tick_size=float(price.get("tickSize", 1.0)),
                min_qty=float(lot.get("minQty", 0.0)),
                min_notional=float(notional.get("minNotional", 0.0)),
            )
            self._precision_cache[symbol] = precision
            return precision
        raise ValueError(f"symbol {symbol} not found in exchangeInfo")

    async def place_order(
        self,
        request: OrderRequest,
        creds: BinanceCreds,
    ) -> Dict[str, Any]:
        if not self._http:
            raise RuntimeError("adapter not started")
        precision = await self.get_precision(request.symbol)
        try:
            quantity, price = validate_and_round(
                qty=request.quantity,
                price=request.price or 0,
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
        payload = {
            "symbol": request.symbol,
            "side": request.side.value,
            "type": "LIMIT_MAKER" if request.strategy.value == "POST_ONLY" else "LIMIT",
            "quantity": quantity,
            "price": price,
            "timestamp": int(time.time() * 1000 + self._time_offset_ms),
            "recvWindow": int(self.config.get("recv_window_ms", 5000)),
        }
        if request.strategy.value == "IOC":
            payload["timeInForce"] = "IOC"
        if request.client_order_id:
            payload["newClientOrderId"] = request.client_order_id
        endpoint = "/api/v3/order"
        signed = self._sign(payload, creds.api_secret)
        headers = {"X-MBX-APIKEY": creds.api_key}
        resp = await self._http.post(endpoint, data=signed, headers=headers)
        if resp.status_code == 429:
            self._metrics["rate_limit_hits"] += 1
        resp.raise_for_status()
        data = resp.json()
        if payload["type"] in {"LIMIT", "LIMIT_MAKER"} and request.ttl_seconds:
            order_id = data.get("orderId")
            if order_id is not None:
                self._schedule_cancel(
                    symbol=request.symbol,
                    order_id=int(order_id),
                    ttl=request.ttl_seconds,
                    creds=creds,
                )
        return data

    def _sign(self, payload: Dict[str, Any], secret: str) -> Dict[str, Any]:
        query = "&".join(f"{k}={payload[k]}" for k in sorted(payload))
        signature = hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()
        payload = dict(payload)
        payload["signature"] = signature
        return payload

    def _schedule_cancel(self, symbol: str, order_id: int, ttl: int, creds: BinanceCreds) -> None:
        async def cancel_task() -> None:
            await asyncio.sleep(ttl)
            await self.cancel_order(symbol=symbol, order_id=order_id, creds=creds)

        task = asyncio.create_task(cancel_task())
        self._cancel_tasks.append(task)

    async def cancel_order(self, symbol: str, order_id: int, creds: BinanceCreds) -> Dict[str, Any]:
        if not self._http:
            raise RuntimeError("adapter not started")
        payload = {
            "symbol": symbol,
            "orderId": order_id,
            "timestamp": int(time.time() * 1000 + self._time_offset_ms),
            "recvWindow": int(self.config.get("recv_window_ms", 5000)),
        }
        signed = self._sign(payload, creds.api_secret)
        headers = {"X-MBX-APIKEY": creds.api_key}
        resp = await self._http.delete("/api/v3/order", data=signed, headers=headers)
        resp.raise_for_status()
        return resp.json()

    def metrics_snapshot(self) -> Dict[str, float]:
        return dict(self._metrics)
