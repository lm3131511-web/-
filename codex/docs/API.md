# API

Codex exposes a minimal HTTP surface implemented in `codex/src/codex/app.py` and
`codex/src/codex/monitoring/health.py`.

## `POST /assess`

Evaluates deterministic features and aggregated sentiment, returning a strict `RiskAssessment` JSON document.

```json
{
  "features": {
    "regime": "bull",
    "rsi_14": 61.2,
    "atr_pct": 0.42,
    "spread_bps": 3.4
  },
  "sentiment": {
    "sentiment_score": -0.6,
    "event_severity": "high",
    "confidence": 0.8,
    "sources_confirmed": 2
  },
  "meta": {
    "mode": "live"
  }
}
```

### Response

```json
{
  "verdict": "DOWNGRADE",
  "size_multiplier": 0.5,
  "risk_tags": ["news_risk"],
  "short_reason": "negative news confirmed",
  "prompt_version": "v2.2.0",
  "cache_hit": false,
  "latency_ms": 134,
  "is_fallback": false,
  "stale_correlation": false
}
```

## `GET /health`

Returns readiness information including Redis connectivity, the active prompt version, and persisted cache hits.

```json
{
  "ok": true,
  "redis": "ok",
  "prompt_version": "v2.2.0",
  "cache_persist_hit_total": 42
}
```

## `GET /metrics`

Prometheus exposition endpoint exported by the FastAPI service.
