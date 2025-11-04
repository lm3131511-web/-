from src.monitoring.metrics import GLOBAL_METRICS


def test_metrics_snapshot_contains_required_fields() -> None:
    snap = GLOBAL_METRICS.snapshot()
    for key in [
        "schema_version",
        "decisions_total",
        "approved_ratio",
        "degradation_mode",
        "alert_queue_backlog",
    ]:
        assert key in snap
