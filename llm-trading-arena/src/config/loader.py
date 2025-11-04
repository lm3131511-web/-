from __future__ import annotations

from pathlib import Path
from typing import Any

from src.vendor import yaml

from .models import AppConfig


def _normalize_config_payload(data: dict[str, Any]) -> dict[str, Any]:
    # Legacy helpers to keep compatibility with earlier configs
    llm = data.get("llm")
    if isinstance(llm, dict):
        reliability = llm.get("reliability")
        if isinstance(reliability, dict):
            if "decay_lambda" in reliability and "lambda" not in reliability:
                reliability["lambda"] = reliability.pop("decay_lambda")
            if "lambda" in reliability:
                reliability["lambda_"] = reliability.pop("lambda")
        emergency = llm.get("emergency_provider")
        if isinstance(emergency, dict):
            guard = emergency.get("safety_guard")
            if guard is None:
                emergency["safety_guard"] = {}
    rolling = data.get("rolling_metrics")
    if isinstance(rolling, dict):
        windows = rolling.get("windows")
        if isinstance(windows, str):
            parts = [part.strip() for part in windows.strip("[]").split(",") if part.strip()]
            rolling["windows"] = [int(part) for part in parts]
    return data


def load_config(path: str | Path) -> AppConfig:
    with Path(path).open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle.read())
    if not isinstance(raw, dict):  # pragma: no cover - defensive branch
        raise TypeError("configuration must be a mapping")
    normalized = _normalize_config_payload(raw)
    return AppConfig.model_validate(normalized)
