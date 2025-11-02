from __future__ import annotations

from typing import Dict, List, Optional

from src.vendor.pydantic import BaseModel, Field


class LLMStageConfig(BaseModel):
    max_tokens: int
    temperature: float
    min_uncertainty: float | None = None
    min_budget_left: float | None = None


class LLMConfig(BaseModel):
    budget_usd_per_min: float
    token_budget_per_tick: int
    aggregator_tau: float
    max_on_demand_features: int
    stages: Dict[str, LLMStageConfig]


class RiskGateConfig(BaseModel):
    limits: Dict[str, float]
    sizing: Dict[str, float]
    market: Dict[str, float]
    cooldowns: Dict[str, float]
    circuit_breakers: Dict[str, float]
    pnl_breaker: Dict[str, float]


class ExecutionConfigModel(BaseModel):
    ttl_sec_range: List[int]
    price_bands_atr_mult: float
    minimal_notional_usd: float
    low_top_depth_usd: float
    strategies: List[str]
    strategy_thresholds: Dict[str, float]
    post_only_queue_penalty_bps: float


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
    assets: Dict[str, Dict[str, float | List[str]] | List[str]]
    llm: LLMConfig
    risk_gate: RiskGateConfig
    execution: ExecutionConfigModel
    monitoring: MonitoringConfig
    exchange: ExchangeConfig
    telegram: TelegramConfig
    symbol_map: Dict[str, str]
    units: Dict[str, float | bool]
    schemas: Dict[str, int]

    model_config = {"extra": "allow"}
