from __future__ import annotations

from prometheus_client import Counter, Histogram


llm_latency = Histogram(
    "codex_llm_latency_ms",
    "LLM latency in milliseconds",
    buckets=(50, 100, 250, 500, 1000, 2000, 4000),
)
verdict_counter = Counter(
    "codex_llm_verdict_total",
    "Total decisions returned by the LLM",
    labelnames=("verdict",),
)
cache_hit_counter = Counter("codex_cache_hit_total", "Cache hits served", labelnames=("source",))
fallback_counter = Counter("codex_fallback_total", "Fallback decisions", labelnames=("reason",))
json_validation_fail_counter = Counter(
    "codex_json_validation_fail_total",
    "JSON validation failures",
)
