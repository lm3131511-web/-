# Runbook — LLM Trading Arena

## Promotion checklist

1. **Paper → Shadow**
   - ✅ Validate schema generation (`python -m src.app.production_pipeline --mode paper`).
   - ✅ Confirm monitoring endpoints return HTTP 200.
   - ✅ Run unit tests (`make test`).

2. **Shadow → Canary**
   - ✅ Configure micro-lot sizing in `config.canary.yaml`.
   - ✅ Ensure Telegram alerts are routed to the canary chat.
   - ✅ Verify risk gates are fail-closed after any breaker event.
   - ✅ Record baseline metrics for `venue_latency_ms_avg`.

3. **Canary → Live**
   - ✅ Canary metrics for seven days: reject rate < 2%, ECE ≤ 0.08, no PnL breaker trips.
   - ✅ Confirm soak test script (`scripts/soak_72h.sh`) is green.
   - ✅ Sign-off from on-call engineer and trading lead.

## Incident response

1. Trigger manual circuit breaker by calling the admin endpoint or toggling the config flag.
2. Switch mode to `shadow` and rehydrate the sqlite journal to avoid replaying idempotent keys.
3. Coordinate with exchange operations for order reconciliation.
