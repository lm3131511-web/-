from __future__ import annotations

from pathlib import Path

from .models import AppConfig

_PROMPT_FILES = [
    "system.md",
    "analyst_A.md",
    "analyst_B.md",
    "analyst_C.md",
]


def _ensure_prompts_exist() -> None:
    prompt_dir = Path(__file__).resolve().parents[2] / "prompts"
    missing = [name for name in _PROMPT_FILES if not (prompt_dir / name).exists()]
    if missing:
        raise FileNotFoundError(f"missing prompt templates: {', '.join(missing)}")


def validate_config(config: AppConfig) -> None:
    _ensure_prompts_exist()
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
    if not isinstance(config.llm.mock_mode, bool):
        raise ValueError("llm.mock_mode must be boolean")
    provider_budgets = config.llm.budget_usd_per_min_per_provider
    for stage_name, stage_cfg in config.llm.stages.items():
        if stage_cfg.mode not in {"stub", "real"}:
            raise ValueError(f"unsupported llm stage mode for {stage_name}")
        if stage_name not in provider_budgets:
            raise ValueError(f"missing per-provider budget for stage {stage_name}")
