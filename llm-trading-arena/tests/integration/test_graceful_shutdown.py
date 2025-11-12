import asyncio

import pytest

from src.app.production_pipeline import TradingArena
from src.config.loader import load_config
from src.config.validators import validate_config


class StubServer:
    def shutdown(self) -> None:  # pragma: no cover - trivial
        pass

    def server_close(self) -> None:  # pragma: no cover - trivial
        pass


class StubAdapter:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def get_next_data(self) -> dict:
        return {"symbol": "BTCUSDT", "bid": 100.0, "ask": 100.1}

    def metrics_snapshot(self) -> dict:
        return {"ts_offset_ms": 0.0}


def test_graceful_shutdown(monkeypatch) -> None:
    async def _run() -> None:
        config = load_config("config.sample.yaml")
        validate_config(config)
        adapter = StubAdapter()
        monkeypatch.setattr("src.app.production_pipeline.build_exchange_adapter", lambda cfg: adapter)
        monkeypatch.setattr("src.app.production_pipeline.start_http_exporter", lambda **_: StubServer())
        arena = TradingArena(config, dry_run=True)
        await arena.initialize()
        await arena.stop()
        assert adapter.started is True
        assert adapter.stopped is True

    asyncio.run(_run())
