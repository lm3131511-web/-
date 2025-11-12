from src.app.production_pipeline import TradingArena
from src.monitoring.health import HealthSnapshot


def test_kill_switch_sets_health_flag() -> None:
    arena = TradingArena.__new__(TradingArena)
    arena._kill_callback_triggered = False
    arena._kill_switch_state = "OFF"
    arena._health = HealthSnapshot(
        ready=True,
        schema_version=1,
        last_snapshot_id="",
        mode="paper",
        venue="binance",
    )
    arena._engage_kill_switch()
    assert arena._kill_switch_state == "ON"
    assert arena._health.kill_switch_state == "ON"
