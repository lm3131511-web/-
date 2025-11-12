# System Requirements Specification — LLM Trading Arena

## Functional requirements

- Ingest Binance Spot miniTicker streams (combined endpoint) and queue them for downstream processing.
- Execute a three-stage LLM analyst pipeline with probabilistic aggregation and calibration.
- Enforce risk limits, cooldowns, and fail-closed circuit breakers.
- Generate execution plans supporting POST_ONLY and IOC strategies with TTL cancellation.
- Persist every decision to JSONL and SQLite with deterministic idempotency keys.
- Emit alerts through a single configurable sink (Telegram or generic webhook). `alerts.mode="none"` is permitted only for local development; canary/live deployments MUST configure Telegram or webhook credentials.

## Non-functional requirements

- Python 3.11+, cross-platform (Linux/Windows).
- Deterministic schemas published under `src/core/schemas_json/`.
- JSONL structured logging and HTTP monitoring served on configurable ports.
- Canary/live tiers must require API keys through environment variables.
- Latency SLO: venue round-trip average < 250 ms, measured via adapter metrics.
- Log rotation defaults: 100 MB maximum per log file, up to 30 archived copies per stream, retention 30 days under `data/logs/archive/`.
- Audit artefacts are persisted to `data/logs/audit.jsonl` and mirrored into SQLite (`decisions.snapshot_id`). Every entry records `ts_utc`, `seed`, `code_hash`, `snapshot_id`, deployment `mode`, and contract version.

## Referee layer

- The execution pipeline includes an explicit Referee stage between Signal and RiskGate. The Referee validates LLM outputs for range/consistency (confidence ∈ [0,1], non-negative size hints, TTL within configured bounds, strategy enabled).
- Referee never overrides the LLM-selected strategy; it only annotates infeasible responses so RiskGate can fail-close the decision.

## Strategy handling

- LLM outputs the definitive strategy (`POST_ONLY`, `IOC`, `POV`, `TWAP`). Execution planner parametrises price/TTL and may mark infeasible but MUST NOT replace the chosen strategy.

## ADV policy

- `assets.adv_table_asof` with `adv_grace_sec` governs staleness. When the ADV table age exceeds the grace window the system treats the table as stale, flips `adv_table_stale=true` in metrics, and enforces `hard_notional_cap_usd` instead of %ADV sizing.
- ADV table source path is declared via `assets.adv_usd_table_path` for reproducible refresh workflows.

## Units guard

- Numeric parameters with domain-specific units expose explicit `_unit` companions (e.g. `max_spread_bps_unit="bps"`, `per_day_loss_pct_unit="%"`).
- `units.enforce=true` activates validation that the provided units are supported and the magnitudes fall inside safe ranges.

## Logging and alerts

- Log rotation parameters (`logging.rotation`) control size-, count-, and age-based archival. All logs rotate into `data/logs/archive/`.
- Alert delivery relies on a persistent queue (`data/logs/alerts.jsonl`) with deduplication and exponential backoff. Alert metrics (`alert_queue_backlog`, `alert_queue_dropped_total`) surface queue health on `/metrics.json`.
