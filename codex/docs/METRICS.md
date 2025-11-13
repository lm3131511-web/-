# Metrics

Codex publishes Prometheus metrics via `/metrics`. The emitters live in
`codex/src/codex/monitoring/metrics.py`.

- `codex_llm_latency_ms` histogram — latency of LLM calls (ms).
- `codex_llm_verdict_total{verdict}` counter — count of verdicts returned.
- `codex_size_multiplier` histogram — distribution of size multipliers.
- `codex_cache_hit_total{source}` counter — in-memory and persisted cache hits.
- `codex_cache_persist_hit_total` counter — decisions served from the SQLite cache.
- `codex_cooldown_skips_total` counter — avoided LLM invocations due to fingerprint cooldown.
- `codex_fallback_total{reason}` counter — fallback responses due to provider or validation failures.
- `codex_json_validation_fail_total` counter — JSON schema validation failures.
- `codex_correlation_stale_total` counter — inputs penalised due to stale correlations.
- `codex_news_events_total{severity}` counter — news events processed by severity.
- `codex_trusted_source_used_total{provider}` counter — trusted source confirmations per provider.
