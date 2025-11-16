from __future__ import annotations

from prometheus_client import Counter, Histogram


llm_latency = Histogram(
    "codex_llm_latency_ms",
    "LLM latency in milliseconds",
    labelnames=("provider",),
    buckets=(50, 100, 250, 500, 1000, 2000, 4000),
)
verdict_counter = Counter(
    "codex_llm_verdict_total",
    "Total decisions returned by the LLM",
    labelnames=("provider", "verdict"),
)
cache_hit_counter = Counter("codex_cache_hit_total", "Cache hits served", labelnames=("source",))
fallback_counter = Counter(
    "codex_fallback_total",
    "Fallback decisions produced or capped",
    labelnames=("provider",),
)
json_validation_fail_counter = Counter(
    "codex_json_validation_fail_total",
    "JSON validation failures",
    labelnames=("provider",),
)
cache_persist_hit_counter = Counter(
    "codex_cache_persist_hit_total",
    "Decisions served from persistent cache",
)
cooldown_skip_counter = Counter(
    "codex_cooldown_skips_total",
    "LLM invocations avoided due to cooldown",
)
correlation_stale_counter = Counter(
    "codex_correlation_stale_total",
    "Occurrences of stale correlation inputs",
)
news_events_counter = Counter(
    "codex_news_events_total",
    "News events ingested by severity",
    labelnames=("severity",),
)
trusted_source_counter = Counter(
    "codex_trusted_source_used_total",
    "Trusted source confirmations by provider",
    labelnames=("provider",),
)
size_multiplier_histogram = Histogram(
    "codex_size_multiplier",
    "Distribution of size multipliers returned",
    buckets=(0.0, 0.1, 0.25, 0.5, 0.75, 1.0),
)
adapter_error_counter = Counter(
    "codex_adapter_error_total",
    "Provider adapter errors",
    labelnames=("provider",),
)
signals_generated_counter = Counter(
    "codex_signals_generated_total",
    "Signals emitted by deterministic strategies",
    labelnames=("strategy",),
)
signals_published_counter = Counter(
    "codex_signals_published_total",
    "Signals released to operators",
    labelnames=("status",),
)
signal_consensus_counter = Counter(
    "codex_signal_consensus_total",
    "Meta-judge verdict distribution",
    labelnames=("result",),
)
