from __future__ import annotations

from pathlib import Path

from src.vendor import yaml

from .models import AppConfig


def load_config(path: str | Path) -> AppConfig:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle.read())
    if isinstance(data, dict):
        llm = data.get("llm")
        if isinstance(llm, dict):
            reliability = llm.get("reliability")
            if isinstance(reliability, dict) and "lambda" in reliability and "decay_lambda" not in reliability:
                reliability["decay_lambda"] = reliability.pop("lambda")
        rolling = data.get("rolling_metrics")
        if isinstance(rolling, dict):
            windows = rolling.get("windows")
            if isinstance(windows, dict) and "windows" in windows:
                rolling["windows"] = windows["windows"]
            elif isinstance(windows, str):
                parts = [part.strip() for part in windows.strip("[]").split(",") if part.strip()]
                rolling["windows"] = [int(part) for part in parts]
    return AppConfig.model_validate(data)
