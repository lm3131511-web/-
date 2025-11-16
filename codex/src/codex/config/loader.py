from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

try:  # Python 3.9+
    from importlib.resources import files as pkg_files
except Exception:  # pragma: no cover - fallback for very old interpreters
    pkg_files = None

import yaml

from .models import Settings


ENV_PATTERN = re.compile(r"\$\{([^}:]+)(?::([^}]*))?\}")


def resolve_config_dir() -> Path:
    """Return the directory containing Codex configuration files."""

    env_dir = os.getenv("CODEX_CONFIG_DIR")
    if env_dir:
        candidate = Path(env_dir)
        if candidate.is_dir():
            return candidate

    default = Path("/app/configs")
    if default.is_dir():
        return default

    if pkg_files is not None:
        try:
            package_path = Path(pkg_files("codex.configs"))
            if package_path.is_dir():
                return package_path
        except Exception:  # pragma: no cover - resource lookup best effort
            pass

    # Repository checkout fallback
    return Path(__file__).resolve().parents[2] / "configs"


def resolve_config_path(filename: str) -> Path:
    """Resolve an individual configuration file path by name."""

    directory = resolve_config_dir()
    candidate = directory / filename
    if candidate.is_file():
        return candidate

    # Final fallback: relative to current working directory
    alt = Path("configs") / filename
    return alt


def load_settings(base: str | Path | None = None, overlay: str | Path | None = None) -> Settings:
    """Load settings by merging base and overlay configuration files."""

    base_path = Path(base) if base else resolve_config_path("base.yaml")
    if not base_path.is_file():  # pragma: no cover - defensive check
        raise FileNotFoundError(f"Base configuration not found: {base_path}")

    data = yaml.safe_load(base_path.read_text(encoding="utf-8")) or {}

    overlay_path: Path | None
    if overlay is not None:
        overlay_path = Path(overlay)
    else:
        env = os.getenv("CODEX_ENV")
        overlay_path = resolve_config_path(f"{env}.yaml") if env else None

    if overlay_path and overlay_path.is_file():
        overlay_data = yaml.safe_load(overlay_path.read_text(encoding="utf-8")) or {}
        data = merge_dicts(data, overlay_data)

    resolved = resolve_env(data)
    return Settings.model_validate(resolved)


__all__ = ["load_settings", "resolve_config_dir", "resolve_config_path"]


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
