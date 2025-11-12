from __future__ import annotations

from pathlib import Path

from .models import AppConfig

_PROMPT_FILES = [
    "system.md",
    "analyst_A.md",
    "analyst_B.md",
    "analyst_C.md",
]


_UNIT_BOUNDS = {
    "%": (0.0, 100.0),
    "bps": (0.0, 100_000.0),
    "usd": (0.0, None),
    "sec": (0.0, None),
    "ms": (0.0, None),
    "ratio": (0.0, 1.0),
    "ticks": (1.0, None),
    "vol_mult": (0.0, None),
}


def _ensure_prompts_exist() -> None:
    prompt_dir = Path(__file__).resolve().parents[2] / "prompts"
    missing = [name for name in _PROMPT_FILES if not (prompt_dir / name).exists()]
    if missing:
        raise FileNotFoundError(f"missing prompt templates: {', '.join(missing)}")


def _validate_alert_mode(config: AppConfig) -> None:
    allowed = {"telegram", "webhook", "none"}
    if config.alerts.mode not in allowed:
        raise ValueError("alerts.mode must be telegram, webhook, or none")
    if config.mode in {"canary", "live"} and config.alerts.mode == "none":
        raise ValueError("alerts.mode='none' is not allowed in canary/live")


def _ensure_unit_bounds(value: float, unit: str, field: str) -> None:
    bounds = _UNIT_BOUNDS.get(unit)
    if bounds is None:
        raise ValueError(f"unsupported unit '{unit}' for {field}")
    minimum, maximum = bounds
    if value < minimum:
        raise ValueError(f"{field} below minimum for unit {unit}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{field} exceeds maximum for unit {unit}")


def _validate_units(config: AppConfig) -> None:
    units_cfg = config.units or {}
    if not units_cfg.get("enforce", False):
        return
    checks = [
        (
            config.risk_gate.limits.per_trade_loss_pct,
            config.risk_gate.limits.per_trade_loss_pct_unit,
            "risk_gate.limits.per_trade_loss_pct",
        ),
        (
            config.risk_gate.limits.per_day_loss_pct,
            config.risk_gate.limits.per_day_loss_pct_unit,
            "risk_gate.limits.per_day_loss_pct",
        ),
        (
            config.risk_gate.limits.max_drawdown_pct,
            config.risk_gate.limits.max_drawdown_pct_unit,
            "risk_gate.limits.max_drawdown_pct",
        ),
        (
            config.risk_gate.market.max_spread_bps,
            config.risk_gate.market.max_spread_bps_unit,
            "risk_gate.market.max_spread_bps",
        ),
        (
            config.execution.max_spread_bps,
            config.execution.max_spread_bps_unit,
            "execution.max_spread_bps",
        ),
        (
            config.execution.minimal_notional_usd,
            config.execution.minimal_notional_usd_unit,
            "execution.minimal_notional_usd",
        ),
        (
            config.execution.low_top_depth_usd,
            config.execution.low_top_depth_usd_unit,
            "execution.low_top_depth_usd",
        ),
        (
            config.execution.post_only_queue_penalty_bps,
            config.execution.post_only_queue_penalty_bps_unit,
            "execution.post_only_queue_penalty_bps",
        ),
        (
            float(config.execution.max_order_age_ms),
            config.execution.max_order_age_ms_unit,
            "execution.max_order_age_ms",
        ),
        (
            config.risk_gate.cooldowns.after_stop_sec,
            config.risk_gate.cooldowns.after_stop_sec_unit,
            "risk_gate.cooldowns.after_stop_sec",
        ),
        (
            config.risk_gate.cooldowns.min_between_trades_sec,
            config.risk_gate.cooldowns.min_between_trades_sec_unit,
            "risk_gate.cooldowns.min_between_trades_sec",
        ),
        (
            config.risk_gate.pnl_breaker.day_loss_pct,
            config.risk_gate.pnl_breaker.day_loss_pct_unit,
            "risk_gate.pnl_breaker.day_loss_pct",
        ),
        (
            config.risk_gate.pnl_breaker.week_loss_pct,
            config.risk_gate.pnl_breaker.week_loss_pct_unit,
            "risk_gate.pnl_breaker.week_loss_pct",
        ),
    ]
    for value, unit, field in checks:
        _ensure_unit_bounds(float(value), str(unit), field)


def validate_config(config: AppConfig) -> None:
    _ensure_prompts_exist()
    _validate_alert_mode(config)
    _validate_units(config)
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
