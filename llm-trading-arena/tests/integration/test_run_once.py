import asyncio
import json
import sqlite3
from pathlib import Path
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
                "storage_dir": str(tmp_path),
                "logging": config.logging.model_copy(
                    update={
                        "paths": config.logging.paths.model_copy(
                            update={
                                "decisions": str(tmp_path / "decisions.jsonl"),
                                "execution": str(tmp_path / "execution.jsonl"),
                                "audit": str(tmp_path / "audit.jsonl"),
                                "alerts": str(tmp_path / "alerts.jsonl"),
                            }
                        )
                    }
                ),
            }
        )

        async def fake_start(self) -> None:  # pragma: no cover - setup shim
            self._http = object()

        async def fake_stop(self) -> None:  # pragma: no cover - teardown shim
            return None

        async def fake_run(self, market_snapshot: dict[str, float]) -> AnalystResponse:
            return AnalystResponse(
                stage="A",
                provider="deepseek",
                prompt_tokens=100,
                completion_tokens=10,
                latency_ms=5.0,
                direction="BUY",
                strategy="POST_ONLY",
                confidence=0.65,
                urgency=0.4,
                size_hint_frac=0.1,
                ttl_hint_sec=45,
                price_band_hint=None,
                uncertainty_hints=["test"],
                requested_features=[],
                reliability=0.7,
                reasoning="",
            )

        arena = TradingArena(config, dry_run=True)
        monkeypatch.setattr(arena.adapter, "start", fake_start.__get__(arena.adapter))
        monkeypatch.setattr(arena.adapter, "stop", fake_stop.__get__(arena.adapter))
        monkeypatch.setattr("src.llm.stages.StageRunner.run", fake_run)

        await arena.initialize()
        arena.adapter.publish_mock_tick({"bid": 100.0, "ask": 100.1, "volatility": 0.01})
        await arena.run_once()

        decisions_path = Path(config.logging.paths.decisions)
        assert decisions_path.exists()
        with decisions_path.open() as handle:
            lines = handle.readlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["status"] in {"approved", "rejected"}

        sqlite_path = Path(config.storage_dir) / config.sqlite_path
        conn = sqlite3.connect(sqlite_path)
        cur = conn.execute("SELECT COUNT(*) FROM decisions")
        assert cur.fetchone()[0] == 1
        conn.close()

        port = arena._http_server.server_port
        with urlopen(f"http://127.0.0.1:{port}/metrics.json") as resp:
            metrics = json.loads(resp.read())
        assert any(name.startswith("decisions_") for name in metrics)
        with urlopen(f"http://127.0.0.1:{port}/health") as resp:
            health = json.loads(resp.read())
        assert health["ready"] is True
        assert "kill_switch_state" in health

        await arena.stop()

    asyncio.run(scenario())
