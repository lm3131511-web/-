from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException

from .config.loader import load_settings
from .config.models import Settings
from .contracts.features import DeterministicFeatures, MetaContext
from .contracts.sentiment import AggregatedSentiment
from .llm_risk.client import LLMRiskClient
from .monitoring.metrics import cache_hit_counter, fallback_counter, llm_latency, verdict_counter

app = FastAPI(title="Codex Risk Service")


def _load_settings() -> Settings:
    config_path = Path(__file__).resolve().parents[2] / "configs" / "base.yaml"
    return load_settings(config_path)


@app.post("/risk")
async def risk_endpoint(
    features: DeterministicFeatures,
    sentiment: AggregatedSentiment,
    meta: MetaContext,
):
    settings = _load_settings()
    client = LLMRiskClient(settings)
    try:
        assessment = await client.evaluate(features=features, sentiment=sentiment, meta=meta)
    except Exception as exc:
        fallback_counter.labels(reason="exception").inc()
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    verdict_counter.labels(verdict=assessment.verdict).inc()
    if assessment.cache_hit:
        cache_hit_counter.labels(source="memory").inc()
    llm_latency.observe(assessment.latency_ms)
    return assessment.model_dump()
