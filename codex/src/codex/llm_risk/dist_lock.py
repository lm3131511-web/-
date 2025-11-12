from __future__ import annotations

import asyncio
import contextlib
import threading
import time
from dataclasses import dataclass
from typing import Optional

try:
    import redis.asyncio as aioredis  # type: ignore
except ImportError:  # pragma: no cover
    aioredis = None  # type: ignore


@dataclass
class LockConfig:
    url: str
    lock_ttl_sec: int
    refresh_interval_ms: int


class DistributedLock:
    def __init__(self, *, redis_url: str, lock_ttl_sec: int, refresh_interval_ms: int) -> None:
        if aioredis is None:
            raise RuntimeError("redis extra is required for distributed locks")
        self.redis_url = redis_url
        self.lock_ttl_sec = lock_ttl_sec
        self.refresh_interval_ms = refresh_interval_ms
        self._client: aioredis.Redis | None = None

    async def _ensure_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(self.redis_url)
        return self._client

    @contextlib.asynccontextmanager
    async def lock(self, key: str, *, timeout_ms: int) -> bool:
        client = await self._ensure_client()
        token = f"lock:{time.time_ns()}"
        end_time = time.monotonic() + timeout_ms / 1000
        acquired = False
        while time.monotonic() < end_time:
            acquired = await client.set(key, token, nx=True, ex=self.lock_ttl_sec)
            if acquired:
                break
            await asyncio.sleep(0.05)
        if not acquired:
            yield False
            return

        stop_event = threading.Event()

        async def refresher() -> None:
            while not stop_event.wait(self.refresh_interval_ms / 1000):
                await client.expire(key, self.lock_ttl_sec)

        task = asyncio.create_task(refresher())
        try:
            yield True
        finally:
            stop_event.set()
            task.cancel()
            with contextlib.suppress(Exception):
                await task
            current_token = await client.get(key)
            if current_token == token.encode():
                await client.delete(key)
