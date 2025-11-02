from __future__ import annotations

import asyncio
import os
from typing import Any, Dict

import pytest

from src.alerts.telegram import TelegramSink
from src.vendor import httpx


class DummyClient:
    def __init__(self) -> None:
        self.calls: list[Dict[str, Any]] = []

    async def __aenter__(self) -> "DummyClient":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        return None

    async def post(self, url: str, json: Dict[str, Any]) -> None:
        self.calls.append({"url": url, "json": json})


def test_deduplication(monkeypatch: pytest.MonkeyPatch) -> None:
    async def scenario() -> None:
        sink = TelegramSink("BOT", "CHAT", dedup_window_sec=60)
        os.environ["BOT"] = "token"
        os.environ["CHAT"] = "chat"
        dummy = DummyClient()
        monkeypatch.setattr(httpx, "AsyncClient", lambda timeout: dummy)
        await sink.publish("msg", level="info")
        await sink.publish("msg", level="info")
        assert len(dummy.calls) == 1

    asyncio.run(scenario())
