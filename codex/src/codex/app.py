from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import REGISTRY, generate_latest
from prometheus_client.exposition import CONTENT_TYPE_LATEST

from .config.loader import load_settings
from .config.models import Settings
from .contracts.features import DeterministicFeatures, MetaContext
from .contracts.sentiment import AggregatedSentiment
from .llm_risk.client import LLMRiskClient
from .monitoring.metrics import cache_hit_counter, fallback_counter, llm_latency, verdict_counter
from .monitoring.health import health as detailed_health, router as health_router

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
async def health(request: Request) -> JSONResponse:
    details = await detailed_health(request)
    status_value = "ok" if details.get("ok", True) else "fail"
    payload = {"status": status_value, **details}
    return JSONResponse(payload, status_code=200)


@app.get("/metrics")
async def metrics() -> Response:
    payload = generate_latest(REGISTRY)
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)


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
