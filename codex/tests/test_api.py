import asyncio

from httpx import AsyncClient

from codex.app import app


def test_health() -> None:
    async def _call() -> None:
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"

    asyncio.run(_call())


def test_metrics() -> None:
    async def _call() -> None:
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/metrics")
        assert response.status_code == 200
        body = response.text
        assert "HELP" in body
        assert "TYPE" in body

    asyncio.run(_call())
