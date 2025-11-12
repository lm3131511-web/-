import os
from pathlib import Path

import pytest

from src.app.production_pipeline import TradingArena
from src.config.loader import load_config
from src.monitoring.metrics import GLOBAL_METRICS


def _build_arena(tmp_path: Path) -> TradingArena:
    cfg = load_config("config.sample.yaml")
    cfg = cfg.model_copy()
    cfg.storage_dir = str(tmp_path)
    cfg.logging.paths.decisions = str(tmp_path / "decisions.jsonl")
    cfg.logging.paths.execution = str(tmp_path / "execution.jsonl")
    cfg.logging.paths.audit = str(tmp_path / "audit.jsonl")
    cfg.logging.paths.alerts = str(tmp_path / "alerts.jsonl")
    cfg.alerts.mode = "none"
    kill_file = tmp_path / "kill.flag"
    cfg.monitoring.http.kill_file_path = str(kill_file)
    arena = TradingArena(cfg, dry_run=True)
    arena._health.ready = True
    return arena


@pytest.fixture(autouse=True)
def _reset_metrics() -> None:
    GLOBAL_METRICS.reset()
    yield
    GLOBAL_METRICS.reset()


def test_kill_switch_prioritises_on_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    arena = _build_arena(tmp_path)
    kill_file = Path(arena._kill_file_path)

    monkeypatch.setenv("KILL_SWITCH", "OFF")
    kill_file.write_text("ON", encoding="utf-8")
    arena._kill_callback_triggered = False
    arena._refresh_kill_switch_state()
    assert arena._kill_switch_state == "ON"

    kill_file.write_text("OFF", encoding="utf-8")
    monkeypatch.setenv("KILL_SWITCH", "ON")
    arena._kill_callback_triggered = False
    arena._refresh_kill_switch_state()
    assert arena._kill_switch_state == "ON"

    monkeypatch.setenv("KILL_SWITCH", "OFF")
    if kill_file.exists():
        kill_file.unlink()
    arena._kill_callback_triggered = True
    arena._refresh_kill_switch_state()
    assert arena._kill_switch_state == "ON"
