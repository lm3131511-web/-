from __future__ import annotations

from .models import AppConfig


def validate_config(config: AppConfig) -> None:
    if config.schemas.get("version") != 2:
        raise ValueError("unsupported schema version")
    if config.execution.ttl_sec_range[0] > config.execution.ttl_sec_range[1]:
        raise ValueError("invalid ttl range")
