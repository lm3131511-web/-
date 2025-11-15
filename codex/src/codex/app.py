from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import REGISTRY, generate_latest

try:  # pragma: no cover - import fallback
    from prometheus_client.exposition import CONTENT_TYPE_LATEST
except Exception:  # pragma: no cover - fallback for older/newer prometheus_client
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

from .config.loader import load_settings
from .config.models import Settings
from .contracts.features import DeterministicFeatures, MetaContext
from .contracts.sentiment import AggregatedSentiment
from .llm_risk.client import LLMRiskClient
from .monitoring.metrics import cache_hit_counter, fallback_counter, llm_latency, verdict_counter
from .monitoring.health import router as health_router

app = FastAPI(title="codex-app", version="1.0.0")
app.include_router(health_router, prefix="/healthz")


def _load_settings() -> Settings:
    config_root = Path(__file__).resolve().parents[2] / "configs"
    base_path = config_root / "base.yaml"
    env = os.getenv("CODEX_ENV")
    overlay_path = config_root / f"{env}.yaml" if env else None
    if overlay_path and not overlay_path.exists():
        overlay_path = None
    return load_settings(base_path, overlay_path)


@app.on_event("startup")
def _populate_state() -> None:
    app.state.settings = _load_settings()


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"}, status_code=200)


@app.get("/metrics")
async def metrics() -> PlainTextResponse:
    payload = generate_latest(REGISTRY)
    return PlainTextResponse(content=payload, media_type=CONTENT_TYPE_LATEST)


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
