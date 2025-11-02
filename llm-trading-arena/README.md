# LLM Trading Arena v1.6

The LLM Trading Arena is a live-ready orchestration layer that combines LLM-based market analysis, strict risk gates, and exchange connectivity for Binance Spot. It supports paper, shadow, canary, and live execution tiers with fail-closed safety.

## Quick start

```bash
make setup
cp .env.sample .env
```

Prepare a configuration (see `config.sample.yaml`) and run the paper pipeline:

```bash
make run-paper
```

To dry-run the full market connectivity in shadow mode:

```bash
make run-shadow
```

Once the canary checklist passes, promote the same build:

```bash
make run-canary
make run-live
```

> **Note:** Canary and live modes require real credentials supplied via environment variables `BINANCE_API_KEY`, `BINANCE_API_SECRET`, `TELEGRAM_BOT_TOKEN`, and `TELEGRAM_CHAT_ID`. Populate `.env` from `.env.sample` or export them before invoking the commands above.

## Testing

```bash
make test
```

## Documentation

- `docs/SRS.md` — system requirements specification.
- `docs/RUNBOOK.md` — operational steps for tier promotions.
- `docs/ACCEPTANCE.md` — acceptance criteria and SLOs.
