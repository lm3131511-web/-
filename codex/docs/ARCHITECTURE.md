# Architecture Overview

Codex is organised around three cooperating subsystems:

1. **News ingest** polls enabled providers (Twitter, Reddit, curated news feeds), sanitises payloads, filters trusted
   sources, aggregates sentiment, and appends immutable records to `data/logs/news_ingest.jsonl`.
2. **Deterministic risk rules** evaluate volatility, correlation quality, deny windows, and high-severity news to apply
   immediate BLOCK/DOWNGRADE gates before the LLM is consulted.
3. **LLM risk client** applies feature fingerprinting, TTL + persistent caching, distributed locking, and strict JSON
   schema validation before logging each verdict to `data/logs/decisions.jsonl`.

Persistence is handled by an in-memory TTL cache backed by SQLite. Prometheus metrics capture latency, cache hits,
cache persistence hits, cooldown skips, fallback counts, stale correlations, and news ingest volumes. The service
exposes `/health`, `/assess`, and `/metrics` endpoints.
