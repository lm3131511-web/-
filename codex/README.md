# Codex v2.2

Codex is a risk and news intelligence module that validates trading features, aggregates sentiment, and requests
LLM verdicts with a strict JSON contract. This repository contains the reference implementation for version 2.2 of the
service, including configuration, prompts, docker manifests, and automated tests that cover the major acceptance
criteria.

The service is model-agnostic and ships with Qwen as the primary provider. DeepSeek and Claude are configured as
sequential fallbacks and can be reordered purely via configuration.

## Project layout
- Код пакета: `src/codex/...`
- Конфиги: `codex/configs/*.yaml`
- Промпты и схемы: `codex/prompts/...`
- Документация: `codex/docs/...`
- Тесты: `codex/tests/...`
- Инфраструктура: `codex/docker/*`, `codex/docker-compose.yml`

## Quick start (локально)
# Команды предполагают запуск из корня монорепозитория (на уровень выше `codex/`).

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[test]
cp codex/.env.example .env  # populate provider credentials via vault/sops
PYTHONPATH=src python scripts/check_config.py
PYTHONPATH=src pytest -q
uvicorn codex.app:app --reload
curl -s http://localhost:8000/health
```

## Docker
```bash
docker compose -f codex/docker-compose.yml up --build
curl -s http://localhost:8000/health
curl -s http://localhost:8000/metrics | head
```

## Data directories
Рабочие файлы создаются на лету:
- `codex/data/logs/decisions.jsonl`
- `codex/data/logs/news_ingest.jsonl`
- `codex/data/cache/codex_cache.db`

В репозитории лежат `.gitkeep`, чтобы каталоги существовали в чистом клоне.

## Signal system overview

Codex now emits discretionary trade ideas through a three-stage LLM ensemble:

1. **LLM-A – Risk Engine (Qwen → DeepSeek → Claude fallbacks)** screens deterministic features and sentiment to ensure
   every candidate respects volatility/news/correlation gates.
2. **LLM-B – Signal Analyst** receives the surviving candidate, validates SL/TP/timeframe, and produces a structured
   explanation JSON for operators.
3. **LLM-C – Meta-Judge** evaluates the risk verdict plus the explanation. During `event_severity="high"` it demands
   consensus from at least two providers before approving publication.

`POST /signals` takes the same payloads as `/risk` (features, sentiment, meta) and returns `FinalSignal` objects that
include BUY/SELL, stop/take levels, risk verdict, consensus state, and human-friendly explanation text. Signals are
logged to `data/logs/signals.jsonl` for audit trails.

Example response:

```json
[
  {
    "instrument": "XAUUSD",
    "timeframe": "M15",
    "side": "buy",
    "entry_price": 2650.5,
    "stop_loss": 2642.0,
    "take_profit": 2675.0,
    "rr_ratio": 3.125,
    "strategy_name": "trend_follow",
    "strategy_confidence": 0.78,
    "risk_verdict": "CONFIRM",
    "llm_confidence": 0.68,
    "risk_tags": ["news_risk"],
    "explanation": "Momentum long remains valid; monitor liquidity",
    "created_at": "2024-06-01T12:15:00Z",
    "valid_until": "2024-06-01T13:45:00Z",
    "risk_reason": "ATR cooling + trusted sources",
    "status": "normal",
    "publish": true,
    "annotations": ["consensus_met"]
  }
]
```

## Tests

The suite covers unit, integration, stress, and property tests.

```bash
PYTHONPATH=src pytest
```

## LLM configuration

Populate `.env` (or your secret manager) with provider credentials. Production environments must source the variables
from Vault/SOPS — do not commit secrets.

```
QWEN_API_KEY=sk-...      # stored outside git
DEEPSEEK_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...
LLM_TIMEOUT_MS=2500
LLM_RETRY_MAX=1
LLM_RETRY_BACKOFF_MS=250
```

Switching the primary model requires only editing `configs/base.yaml` (or the overlay in use) to set `llm.primary` and
optionally reordering `llm.fallback_chain`.

## Budget & Alerts

Set provider-side spend caps before enabling live traffic. Alibaba Cloud (DashScope) budgets and alerts can be configured
through the console; DeepSeek and Anthropic expose per-key usage dashboards. Codex exports the following Prometheus
metrics for budget guardrails:

- `codex_llm_latency_ms{provider}` — latency histogram per provider (track p95 SLA).
- `codex_llm_verdict_total{provider,verdict}` — decision distribution.
- `codex_json_validation_fail_total{provider}` — schema drift and injection failures.
- `codex_fallback_total{provider}` — capped decisions after fallback routing.
- `codex_adapter_error_total{provider}` — transport or API errors.

Recommended alerts:

- p95 latency exceeds the configured SLA window.
- Burst in JSON validation failures or adapter errors.
- Elevated fallback counts (can indicate upstream issues or budget exhaustion).
