from __future__ import annotations

from pathlib import Path

from src.vendor import yaml

from .models import AppConfig


def load_config(path: str | Path) -> AppConfig:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle.read())
    return AppConfig.model_validate(data)
