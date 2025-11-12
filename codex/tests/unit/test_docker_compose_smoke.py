from pathlib import Path

import yaml


def test_docker_compose_services_present():
    compose_path = Path(__file__).resolve().parents[2] / "docker-compose.yml"
    data = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    services = data.get("services", {})
    assert "codex-app" in services
    assert "redis" in services
    assert services["codex-app"]["build"]["dockerfile"] == "docker/Dockerfile.app"
    assert services["codex-worker"]["build"]["dockerfile"] == "docker/Dockerfile.worker"
