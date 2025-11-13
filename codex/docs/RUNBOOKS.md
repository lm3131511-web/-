# Codex Runbooks

## Cold Start / Post-Rollback
1. Flush Redis fingerprint and correlation caches.
2. Run correlation pre-computation job (placeholder `_perform_cold_start()` hook in `codex/src/codex/bootstrap.py`).
3. Enable `quant_only_mode` for 15 minutes to warm caches.
4. Monitor `codex_cache_persist_hit_total` and `codex_cache_hit_total`; re-enable LLM evaluation when both counters rise.

## LLM Incident
1. Toggle `quant_only_mode` so the skeleton can continue without LLM decisions.
2. Inspect provider dashboards for service degradation and rate-limit breaches.
3. Verify `codex_fallback_total` and `codex_json_validation_fail_total` metrics.
4. Execute `codex/tests/stress/test_llm_api_schema_drift.py` to confirm schema stability.

## News Blackout
1. Confirm provider credentials and ingest health (`codex/data/logs/news_ingest.jsonl`).
2. Enable backup RSS feeds and reduce `sentiment_confidence_threshold` temporarily.
3. Notify trading to increase manual oversight until feeds recover.
