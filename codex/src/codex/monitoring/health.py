from __future__ import annotations

import os

from fastapi import APIRouter, Request
import redis.asyncio as aioredis

from .metrics import cache_persist_hit_counter

router = APIRouter()


@router.get("/health")
@router.get("/")
async def health(request: Request) -> dict[str, object]:
    app = request.app
    settings = getattr(app.state, "settings", None)
    redis_status = "unknown"
    ok = True
    redis_url = os.getenv("REDIS_URL")
    if settings and not redis_url:
        redis_url = settings.llm_risk.distributed.url
    if redis_url:
        try:
            async with aioredis.from_url(redis_url) as client:
                pong = await client.ping()
            redis_status = "ok" if pong else "fail"
            ok = ok and pong
        except Exception:  # pragma: no cover - network failure path
            redis_status = "fail"
            ok = False
    payload = {
        "ok": ok,
        "redis": redis_status,
        "prompt_version": getattr(settings, "prompt_version", "unknown") if settings else "unknown",
        "cache_persist_hit_total": cache_persist_hit_counter.total(),
    }
    return payload
