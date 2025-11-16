# Software Requirements Specification

* Codex shall accept deterministic features, aggregated sentiment, and meta context as input.
* Codex shall return a `RiskAssessment` JSON object conforming to `prompts/schemas/llm_risk_assessment.schema.json`.
* Codex shall fail closed by returning a `DOWNGRADE` verdict with `llm_fallback` tag when the provider response is invalid.
* Codex shall persist risk assessments for the configured TTL and rehydrate them on restart.
* Codex shall expose Prometheus metrics defined in `docs/METRICS.md`.
* Codex shall provide runbooks for cold start, incident response, and news blackout scenarios.
