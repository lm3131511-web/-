from src.monitoring.metrics import GLOBAL_METRICS


def test_metrics_snapshot_contains_required_fields() -> None:
    GLOBAL_METRICS.reset()
    snap = GLOBAL_METRICS.snapshot()
    expectations = {
        "schema_version": int,
        "decisions_total": int,
        "approved_ratio": float,
        "risk_blocked_total": int,
        "degradation_mode": str,
        "u_score": float,
        "llm_cost_per_min": float,
        "llm_cost_per_min_A": float,
        "llm_cost_per_min_B": float,
        "llm_cost_per_min_C": float,
        "llm_token_usage_per_provider": dict,
        "prompt_versions": dict,
        "prompt_hashes": dict,
        "weights_used": dict,
        "approved_by_strategy": dict,
        "llm_json_repair_rate": float,
        "alert_queue_backlog": int,
        "alert_queue_dropped_total": int,
        "adv_table_stale": bool,
        "kill_switch_state": str,
    }
    for field, expected_type in expectations.items():
        assert field in snap
        assert isinstance(snap[field], expected_type)
    hashes = snap["prompt_hashes"]
    for value in hashes.values():
        assert isinstance(value, str)
        assert len(value) >= 0
