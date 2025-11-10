from types import SimpleNamespace

import pytest

from src.app.production_pipeline import TradingArena
from src.monitoring.health import HealthSnapshot


def _arena_with_skew(skew: float) -> TradingArena:
    arena = TradingArena.__new__(TradingArena)
    arena.adapter = SimpleNamespace(metrics_snapshot=lambda: {"ts_offset_ms": skew})
    arena.config = SimpleNamespace(
        exchange=SimpleNamespace(
            max_clock_skew_ms=100.0,
            api_key_env="",
            api_secret_env="",
            name="binance_spot",
        ),
        mode="paper",
    )
    arena._health = HealthSnapshot(
        ready=True,
        schema_version=1,
        last_snapshot_id="",
        mode="paper",
        venue="binance",
    )
    arena.mode = "paper"
    arena.dry_run = True
    return arena


def test_time_sync_guard_passes_within_bounds() -> None:
    arena = _arena_with_skew(50.0)
    arena._enforce_time_sync()
    assert "time_sync" not in arena._health.breakers


def test_time_sync_guard_blocks_excessive_skew() -> None:
    arena = _arena_with_skew(500.0)
    with pytest.raises(RuntimeError):
        arena._enforce_time_sync()
    assert arena._health.breakers.get("time_sync") is True
