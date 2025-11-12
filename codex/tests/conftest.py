from pathlib import Path

import pytest

from codex.config.loader import load_settings
from codex.config.models import Settings


@pytest.fixture(scope="session")
def settings() -> Settings:
    config_path = Path(__file__).resolve().parents[1] / "configs" / "base.yaml"
    return load_settings(config_path)
