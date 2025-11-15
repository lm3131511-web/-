import pytest
from fastapi.testclient import TestClient

from codex.app import app


class DummyRedis:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def ping(self):
        return True


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("CODEX_ENV", "dev")
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setattr("codex.monitoring.health.aioredis.from_url", lambda url: DummyRedis())
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint_reports_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_healthz_reports_details(client):
    response = client.get("/healthz/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["redis"] in {"ok", "unknown"}
    assert payload["prompt_version"] == "v2.2.0"
    assert "cache_persist_hit_total" in payload
