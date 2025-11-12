# Codex Runbooks

## Cold Start / Post-Rollback
1. Flush Redis fingerprint and correlation caches.
2. Run correlation pre-computation job with the `--force` flag.
3. Keep `quant_only_mode` enabled for 15 minutes to warm caches.
4. Re-enable LLM evaluation once `codex_cache_persist_hit_total` starts increasing.

## LLM Incident
1. Toggle `quant_only_mode` so the skeleton can continue without LLM decisions.
2. Inspect provider dashboards for service degradation.
3. Verify `codex_fallback_total` and `codex_json_validation_fail_total` metrics.
4. Execute the `tests/stress/test_llm_api_schema_drift.py` regression to confirm schema stability.

## News Blackout
1. Confirm provider credentials and ingest health.
2. Enable backup RSS feeds and reduce the `sentiment_confidence_threshold` temporarily.
3. Notify trading to increase manual oversight until feeds recover.
