# Metrics

| Metric | Type | Labels | Description |
| --- | --- | --- | --- |
| `codex_llm_latency_ms` | Histogram | `quantile` | LLM request latency distribution. |
| `codex_llm_verdict_total` | Counter | `verdict` | Count of LLM verdicts produced. |
| `codex_cache_hit_total` | Counter | `source` | Memory or persistence cache hits. |
| `codex_fallback_total` | Counter | `reason` | Fallback invocations triggered by errors. |
| `codex_json_validation_fail_total` | Counter | – | Schema validation failures from providers. |
