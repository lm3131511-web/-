from fastapi.testclient import TestClient

from codex.app import app


client = TestClient(app)


def test_health_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json().get("status") == "ok"


def test_metrics_ok() -> None:
    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.text
    assert "# HELP" in body or "codex_llm_latency_ms" in body
    assert "text/plain" in response.headers.get("content-type", "")
