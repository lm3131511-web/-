from pathlib import Path
import importlib.util
import sys

import pytest


def _prime_stubs() -> None:
    stub_root = Path(__file__).resolve().parent / "_stubs"
    if not stub_root.exists():
        return
    needs_stub = any(
        importlib.util.find_spec(pkg) is None
        for pkg in (
            "fastapi",
            "httpx",
            "hypothesis",
            "jsonschema",
            "prometheus_client",
            "pydantic",
            "redis",
            "yaml",
        )
    )
    if needs_stub:
        sys.path.insert(0, str(stub_root))


_prime_stubs()

from codex.config.loader import load_settings
from codex.config.models import Settings


@pytest.fixture(scope="session")
def settings() -> Settings:
    config_path = Path(__file__).resolve().parents[1] / "configs" / "base.yaml"
    return load_settings(config_path)
