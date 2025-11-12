from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.vendor.pydantic import BaseModel, Field


class LLMStageConfig(BaseModel):
    provider: str
    mode: str = Field(default="stub")
    max_tokens: int
    temperature: float
    min_uncertainty: float | None = None
    min_budget_left: float | None = None
    prompt_version: str = "v1"


class LLMReliabilityConfig(BaseModel):
    window: int = Field(ge=1)
    lambda_: float = Field(alias="lambda", ge=0.0)
    update_every_n: int = Field(default=200, ge=1)
    update_every_min: int = Field(default=15, ge=1)
    min_interval_min: int = Field(default=5, ge=1)

    model_config = {"populate_by_name": True}


class AdaptiveBudgetingConfig(BaseModel):
    enabled: bool = True
    min_frac: float = Field(default=0.6, ge=0.0, le=1.0)
    risk_weight: float = Field(default=0.4, ge=0.0, le=1.0)


class EmergencySafetyGuardConfig(BaseModel):
    force_flat_on_uncertainty: bool = True
    max_urgency: float = Field(default=0.2, ge=0.0, le=1.0)


class EmergencyProviderConfig(BaseModel):
    enabled: bool = False
    name: str = "tinyllama"
    max_tokens: int = 256
    safety_guard: EmergencySafetyGuardConfig = EmergencySafetyGuardConfig()


class DegradationConfig(BaseModel):
    u_enter: float = Field(default=0.55, ge=0.0, le=1.0)
    budget_enter_pct: float = Field(default=8.0, ge=0.0, le=100.0)
    u_exit: float = Field(default=0.40, ge=0.0, le=1.0)
    budget_exit_pct: float = Field(default=30.0, ge=0.0, le=100.0)
    min_emergency_min: int = Field(default=15, ge=1)


class LLMConfig(BaseModel):
    budget_usd_per_min: float = Field(default=0.0, ge=0.0)
    budget_usd_per_min_per_provider: Dict[str, float] = Field(default_factory=dict)
    per_mode_budget_usd_per_min: Dict[str, float]
    token_budget_per_tick: int
    max_on_demand_features: int
    aggregator_tau: float
    stages: Dict[str, LLMStageConfig]
    reliability: LLMReliabilityConfig
    adaptive_budgeting: AdaptiveBudgetingConfig
    emergency_provider: EmergencyProviderConfig
    degradation: DegradationConfig
    mock_mode: bool = False


class RiskLimitsConfig(BaseModel):
    per_trade_loss_pct: float
    per_trade_loss_pct_unit: str = "%"
    per_day_loss_pct: float
    per_day_loss_pct_unit: str = "%"
    max_drawdown_pct: float
    max_drawdown_pct_unit: str = "%"


class RiskSizingConfig(BaseModel):
    pos_cap_per_asset_pct: float
    pos_cap_per_asset_pct_unit: str = "%"
    cluster_cap_pct: float
    cluster_cap_pct_unit: str = "%"


class RiskMarketConfig(BaseModel):
    max_spread_bps: float
    max_spread_bps_unit: str = "bps"


class RiskCooldownConfig(BaseModel):
    after_stop_sec: float
    after_stop_sec_unit: str = "sec"
    min_between_trades_sec: float
    min_between_trades_sec_unit: str = "sec"


class RiskCircuitBreakersConfig(BaseModel):
    ece_threshold: float
    ece_threshold_unit: str = "ratio"
    hitrate_drop_window: int
    hitrate_drop_window_unit: str = "ticks"


class RiskPnLBreakerConfig(BaseModel):
    day_loss_pct: float
    day_loss_pct_unit: str = "%"
    week_loss_pct: float
    week_loss_pct_unit: str = "%"


class RiskGateConfig(BaseModel):
    limits: RiskLimitsConfig
    sizing: RiskSizingConfig
    market: RiskMarketConfig
    cooldowns: RiskCooldownConfig
    circuit_breakers: RiskCircuitBreakersConfig
    pnl_breaker: RiskPnLBreakerConfig


class SlicingPerAssetConfig(BaseModel):
    depth_imbalance_buy_cutoff: float | None = None
    depth_imbalance_sell_cutoff: float | None = None
    aggression_cut_frac: float | None = None


class SlicingConfig(BaseModel):
    enabled: bool = True
    pov_slice_frac_of_curr_vol: float = 0.1
    min_notional_usd: float = 10.0
    per_asset: Dict[str, SlicingPerAssetConfig] | None = None


class ExecutionConfigModel(BaseModel):
    enforce_exchange_filters: bool
    ttl_sec_range: List[int]
    price_bands_vol_mult: float
    price_bands_vol_mult_unit: str = "vol_mult"
    minimal_notional_usd: float
    minimal_notional_usd_unit: str = "usd"
    low_top_depth_usd: float
    low_top_depth_usd_unit: str = "usd"
    max_spread_bps: float
    max_spread_bps_unit: str = "bps"
    strategies: List[str]
    strategy_thresholds: Dict[str, float]
    post_only_queue_penalty_bps: float
    post_only_queue_penalty_bps_unit: str = "bps"
    max_order_age_ms: int
    max_order_age_ms_unit: str = "ms"
    slicing: SlicingConfig


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


class LogRotationConfig(BaseModel):
    max_file_mb: int = 100
    max_files_per_stream: int = 30
    max_retention_days: int = 30


class LoggingConfig(BaseModel):
    level: str
    paths: LoggingPaths
    rotation: LogRotationConfig = LogRotationConfig()


class MonitoringHTTPConfig(BaseModel):
    bind: str = "127.0.0.1"
    auth_token_env: str | None = None
    kill_rate_limit_per_min: int = 1
    kill_file_path: Optional[str] = None


class MonitoringConfig(BaseModel):
    metrics_port: int
    health_interval_sec: int
    http: MonitoringHTTPConfig


class AlertsConfig(BaseModel):
    mode: str = "none"
    min_level: str = "info"
    dedup_window_sec: int = 60


class TimeSyncNTPConfig(BaseModel):
    enabled: bool = True
    host: str = "pool.ntp.org"
    threshold_ms: int = 500


class TimeSyncFallbackPolicy(BaseModel):
    auto_switch_to_ntp: bool = True
    alert_on_switch: str = "critical"


class TimeSyncConfig(BaseModel):
    mode: str = "exchange"
    max_exchange_failures: int = 3
    fallback_policy: TimeSyncFallbackPolicy = TimeSyncFallbackPolicy()
    ntp: TimeSyncNTPConfig = TimeSyncNTPConfig()


class AdaptersConfig(BaseModel):
    time_sync: TimeSyncConfig


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
    alerts: AlertsConfig
    adapters: AdaptersConfig
    exchange: ExchangeConfig
    telegram: TelegramConfig
    units: Dict[str, float | bool]
    schemas: Dict[str, int]
    storage_dir: str = "data"
    sqlite_path: str = "arena.sqlite3"

    model_config = {"extra": "allow"}
