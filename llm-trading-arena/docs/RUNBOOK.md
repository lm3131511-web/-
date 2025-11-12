# Runbook — LLM Trading Arena

## Promotion checklist

1. **Paper → Shadow**
   - ✅ Validate schema generation (`python -m src.app.production_pipeline --mode paper`).
   - ✅ Confirm monitoring endpoints return HTTP 200.
   - ✅ Run unit tests (`make test`).

2. **Shadow → Canary**
   - ✅ Configure micro-lot sizing in `config.canary.yaml`.
   - ✅ Ensure Telegram alerts are routed to the canary chat.
   - ✅ Validate `alerts.mode` is **not** set to `none`; promotion blocks until a real sink (Telegram/webhook) is configured.
   - ✅ Verify risk gates are fail-closed after any breaker event.
   - ✅ Record baseline metrics for `venue_latency_ms_avg`.

3. **Canary → Live**
   - ✅ Canary metrics for seven days: reject rate < 2%, ECE ≤ 0.08, no PnL breaker trips.
   - ✅ Confirm soak test script (`scripts/soak_72h.sh`) is green.
   - ✅ Sign-off from on-call engineer and trading lead.
   - ✅ Confirm `/metrics.json` reports `adv_table_stale=false` or document the fallback to `hard_notional_cap_usd`.

## Prompt update procedure

1. Raise a PR with changes to `prompts/*.md`, run `pytest -q`, and confirm the prompt hash unit guard passes.
2. Verify locally that `/metrics.json` exposes updated `prompt_versions` and `prompt_hashes` for the modified stages before merge.
3. After deploy, run `make run-shadow` for 2–4 hours; ensure `llm_json_repair_rate < 0.01` and prompt hashes remain stable throughout the soak.
4. Promote to canary only when the shadow soak is green and alert deduplication behaves as expected.

## Kill switch management

- Sources: environment variable `KILL_SWITCH`, file flag (`monitoring.http.kill_file_path`), and HTTP `POST /kill` (with `X-Auth-Token`). Any source asserting `ON` keeps the switch engaged until cleared.
- To clear a file-triggered kill, remove or update the kill flag file and confirm `/health.kill_switch_state` flips back to `OFF`.
- Document any kill activation in the incident channel and include the triggering source in the postmortem.

## Incident response

1. Trigger manual circuit breaker by calling the admin endpoint or toggling the config flag.
2. Switch mode to `shadow` and rehydrate the sqlite journal to avoid replaying idempotent keys.
3. Coordinate with exchange operations for order reconciliation.
