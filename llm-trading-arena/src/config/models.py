from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.vendor.pydantic import BaseModel, Field


class LLMStageConfig(BaseModel):
    provider: str
    max_tokens: int
    temperature: float
    min_uncertainty: float | None = None
    min_budget_left: float | None = None


class LLMReliabilityConfig(BaseModel):
    window: int = Field(ge=1)
    decay_lambda: float = Field(ge=0.0)


class LLMConfig(BaseModel):
    budget_usd_per_min: float
    token_budget_per_tick: int
    aggregator_tau: float
    max_on_demand_features: int
    stages: Dict[str, LLMStageConfig]
    reliability: LLMReliabilityConfig


class RiskGateConfig(BaseModel):
    limits: Dict[str, float]
    sizing: Dict[str, float]
    market: Dict[str, float]
    cooldowns: Dict[str, float]
    circuit_breakers: Dict[str, float]
    pnl_breaker: Dict[str, float]


class ExecutionConfigModel(BaseModel):
    enforce_exchange_filters: bool
    ttl_sec_range: List[int]
    price_bands_vol_mult: float
    minimal_notional_usd: float
    low_top_depth_usd: float
    strategies: List[str]
    strategy_thresholds: Dict[str, float]
    post_only_queue_penalty_bps: float


class EconomicsConfig(BaseModel):
    stress_slippage_prob: float
    normal: Dict[str, float]
    stress: Dict[str, float]


class CalendarWindow(BaseModel):
    tag: str
    start_utc: str
    end_utc: str
    weekdays: List[int]


class CalendarConfig(BaseModel):
    timezone: str
    blackout_windows: List[CalendarWindow]
    overrides: List[Dict[str, str]]
    events_utc: List[str]


class RollingMetricsConfig(BaseModel):
    windows: List[int]
    min_samples: int


class OrderManagementConfig(BaseModel):
    deduplication_window_sec: int
    retries: int
    idempotency_prefix: str


class LoggingPaths(BaseModel):
    decisions: str
    execution: str
    audit: str
    alerts: str


class LoggingConfig(BaseModel):
    level: str
    paths: LoggingPaths


class MonitoringConfig(BaseModel):
    metrics_port: int
    health_interval_sec: int
    alert_sink: str
    alert_min_level: str
    alert_dedup_window_sec: int


class ExchangeConfig(BaseModel):
    name: str
    base_url: str
    ws_url: str
    recv_window_ms: int
    account_type: str
    time_sync_sec: int
    max_clock_skew_ms: int
    precision_cache_ttl_sec: int
    api_key_env: str
    api_secret_env: str


class TelegramConfig(BaseModel):
    bot_token_env: str
    chat_id_env: str


class AppConfig(BaseModel):
    mode: str
    dry_run: bool
    sell_enabled: bool = True
    assets: Dict[str, Any]
    llm: LLMConfig
    risk_gate: RiskGateConfig
    execution: ExecutionConfigModel
    economics: EconomicsConfig
    calendar: CalendarConfig
    rolling_metrics: RollingMetricsConfig
    order_management: OrderManagementConfig
    logging: LoggingConfig
    monitoring: MonitoringConfig
    exchange: ExchangeConfig
    telegram: TelegramConfig
    units: Dict[str, float | bool]
    schemas: Dict[str, int]
    storage_dir: str = "data"
    sqlite_path: str = "arena.sqlite3"

    model_config = {"extra": "allow"}
