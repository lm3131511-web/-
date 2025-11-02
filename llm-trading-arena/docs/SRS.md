# System Requirements Specification — LLM Trading Arena

## Functional requirements

- Ingest Binance Spot miniTicker streams (combined endpoint) and queue them for downstream processing.
- Execute a three-stage LLM analyst pipeline with probabilistic aggregation and calibration.
- Enforce risk limits, cooldowns, and fail-closed circuit breakers.
- Generate execution plans supporting POST_ONLY and IOC strategies with TTL cancellation.
- Persist every decision to JSONL and SQLite with deterministic idempotency keys.
- Emit alerts through Telegram with deduplication and publish HTTP monitoring endpoints.

## Non-functional requirements

- Python 3.11+, cross-platform (Linux/Windows).
- Deterministic schemas published under `src/core/schemas_json/`.
- JSONL structured logging and HTTP monitoring served on configurable ports.
- Canary/live tiers must require API keys through environment variables.
- Latency SLO: venue round-trip average < 250 ms, measured via adapter metrics.
