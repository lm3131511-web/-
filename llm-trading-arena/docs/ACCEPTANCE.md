# Acceptance Criteria — LLM Trading Arena

1. **Contract integrity** — JSON schemas generated under `src/core/schemas_json/` match Pydantic models during CI.
2. **Observability** — `/metrics.json` and `/health` respond with HTTP 200 and include latest snapshot identifiers.
3. **Risk posture** — Fail-closed behaviour is validated when risk gates reject a trade due to breaker triggers.
4. **Telegram alerts** — Approved decisions emit formatted alerts with plan, probabilities, and mode context.
5. **Execution controls** — Canary mode submits micro-lot orders only when API keys are present and dry-run is disabled.
6. **Promotion readiness** — Seven-day canary soak meets reject-rate, calibration, and latency SLOs prior to live promotion.
