from __future__ import annotations

from .models import AppConfig


def validate_config(config: AppConfig) -> None:
    if int(config.schemas.get("version", 0)) != 1:
        raise ValueError("unsupported schema version")
    ttl_min, ttl_max = config.execution.ttl_sec_range
    if ttl_min <= 0 or ttl_max <= 0 or ttl_min > ttl_max:
        raise ValueError("invalid ttl range")
    if config.execution.enforce_exchange_filters and "POST_ONLY" not in config.execution.strategies:
        raise ValueError("POST_ONLY strategy must be present when filters are enforced")
    if config.llm.aggregator_tau <= 0:
        raise ValueError("aggregator_tau must be positive")
    if config.monitoring.http.kill_rate_limit_per_min <= 0:
        raise ValueError("kill switch rate limit must be positive")
