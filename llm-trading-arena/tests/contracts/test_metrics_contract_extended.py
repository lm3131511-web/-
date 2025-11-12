from src.monitoring.metrics import GLOBAL_METRICS


def test_metrics_snapshot_extended_contract() -> None:
    GLOBAL_METRICS.reset()
    snap = GLOBAL_METRICS.snapshot()
    expected_keys = [
        "prompt_versions",
        "prompt_hashes",
        "weights_used",
        "llm_cost_per_min",
        "llm_cost_per_min_A",
        "llm_cost_per_min_B",
        "llm_cost_per_min_C",
        "llm_token_usage_per_provider",
        "approved_by_strategy",
        "llm_json_repair_rate",
        "budget_sentry_hits",
    ]
    for key in expected_keys:
        assert key in snap
    assert isinstance(snap["prompt_versions"], dict)
    assert isinstance(snap["prompt_hashes"], dict)
    assert isinstance(snap["weights_used"], dict)
    assert isinstance(snap["llm_token_usage_per_provider"], dict)
    assert set(snap["approved_by_strategy"].keys()) >= {"POST_ONLY", "IOC", "POV", "TWAP"}
