# Architecture Overview

Codex is organised around three layers:

1. **News pipeline** sanitises provider payloads, filters trusted sources, and aggregates sentiment into a compact
   `AggregatedSentiment` contract.
2. **Risk rules** perform deterministic gating on volatility, news severity, correlation quality, and deny windows before
   any LLM call is made.
3. **LLM client** applies feature fingerprinting, cache lookups, and distributed locking before invoking the selected
   provider. Responses are validated against the strict JSON schema and persisted for auditability.

Persistence is handled by an in-memory TTL cache backed by SQLite. Prometheus metrics capture latency, cache hits,
fallbacks, and schema validation failures.
