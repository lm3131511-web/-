from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path
from typing import Any
from urllib.request import urlopen

import pytest

from src.app.production_pipeline import TradingArena
from src.config.loader import load_config
from src.core.contracts import AnalystResponse


def test_run_once_writes_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def scenario() -> None:
        config = load_config("config.sample.yaml")
        config = config.model_copy(
            update={
                "monitoring": config.monitoring.model_copy(update={"metrics_port": 0}),
                "mode": "shadow",
            }
        )
        config.model_extra["storage_dir"] = str(tmp_path)

        async def fake_start(self: Any) -> None:
            self._http = object()

        async def fake_stop(self: Any) -> None:
            return None

        async def fake_run(self: Any, market_snapshot: dict[str, float]) -> AnalystResponse:
            return AnalystResponse(
                stage="A",
                prompt_tokens=100,
                completion_tokens=10,
                latency_ms=5.0,
                decision_confidence=0.6,
                recommended_action="BUY",
                reasoning="",
            )

        arena = TradingArena(config, dry_run=True)
        monkeypatch.setattr(arena.adapter, "start", fake_start.__get__(arena.adapter))
        monkeypatch.setattr(arena.adapter, "stop", fake_stop.__get__(arena.adapter))
        monkeypatch.setattr("src.llm.stages.StageRunner.run", fake_run)

        await arena.initialize()
        arena.adapter.publish_mock_tick({"bid": 100.0, "ask": 100.1, "volatility": 0.01})
        await arena.run_once()

        jsonl_path = Path(tmp_path) / "decisions.jsonl"
        assert jsonl_path.exists()
        with jsonl_path.open() as handle:
            lines = handle.readlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["status"] in {"approved", "rejected"}

        sqlite_path = Path(tmp_path) / "arena.sqlite3"
        conn = sqlite3.connect(sqlite_path)
        cur = conn.execute("SELECT COUNT(*) FROM final_decisions")
        assert cur.fetchone()[0] == 1
        conn.close()

        port = arena._http_server.server_port
        with urlopen(f"http://127.0.0.1:{port}/metrics.json") as resp:
            metrics = json.loads(resp.read())
        assert any(name.startswith("decisions_") for name in metrics)
        with urlopen(f"http://127.0.0.1:{port}/health") as resp:
            health = json.loads(resp.read())
        assert health["ready"] is True

        await arena.stop()

    asyncio.run(scenario())
