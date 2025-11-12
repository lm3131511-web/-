from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .models import Settings


@dataclass(frozen=True)
class ConfigPaths:
    base: Path
    overlay: Path | None = None


def load_settings(base: str | Path, overlay: str | Path | None = None) -> Settings:
    base_path = Path(base)
    data = yaml.safe_load(base_path.read_text(encoding="utf-8")) or {}
    if overlay:
        overlay_path = Path(overlay)
        overlay_data = yaml.safe_load(overlay_path.read_text(encoding="utf-8")) or {}
        data = merge_dicts(data, overlay_data)
    return Settings.model_validate(data)


def merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result
