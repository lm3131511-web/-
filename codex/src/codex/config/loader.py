from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .models import Settings


@dataclass(frozen=True)
class ConfigPaths:
    base: Path
    overlay: Path | None = None


ENV_PATTERN = re.compile(r"\$\{([^}:]+)(?::([^}]*))?\}")


def load_settings(base: str | Path, overlay: str | Path | None = None) -> Settings:
    base_path = Path(base)
    data = yaml.safe_load(base_path.read_text(encoding="utf-8")) or {}
    if overlay:
        overlay_path = Path(overlay)
        overlay_data = yaml.safe_load(overlay_path.read_text(encoding="utf-8")) or {}
        data = merge_dicts(data, overlay_data)
    resolved = resolve_env(data)
    return Settings.model_validate(resolved)


def merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def resolve_env(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: resolve_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve_env(v) for v in value]
    if isinstance(value, str):
        def replace(match: re.Match[str]) -> str:
            var, default = match.group(1), match.group(2)
            return os.getenv(var, default or "")

        return ENV_PATTERN.sub(replace, value)
    return value
