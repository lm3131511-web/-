from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RetryConfig(BaseModel):
    max: int = Field(ge=0, default=1)
    backoff_ms: int = Field(ge=0, default=250)


class LLMConfig(BaseModel):
    primary: str
    timeout_ms: int = Field(ge=0, default=2500)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    max_ctx_tokens: int = Field(ge=0, default=32000)
    output_json_schema: str


class RuntimeConfig(BaseModel):
    environment: str = "base"
    quant_only_mode: bool = False
    cold_start: bool = False


class PersistenceConfig(BaseModel):
    enabled: bool = True
    backend: str = "sqlite"
    path: str


class CacheConfig(BaseModel):
    ttl_sec: int = Field(ge=0, default=240)
    max_items: int = Field(ge=1, default=5000)
    persistence: PersistenceConfig


class DistributedConfig(BaseModel):
    enabled: bool = True
    backend: str = "redis"
    url: str
    lock_ttl_sec: int = 60
    lock_acquire_timeout_ms: int = 500
    lock_refresh_interval_ms: int = 10000


class FallbackConfig(BaseModel):
    enable_quant_only_after_failures: int = 3
    max_size_multiplier: float = Field(ge=0.0, le=1.0, default=0.3)


class FeatureFingerprintConfig(BaseModel):
    fields: List[str]
    deltas: Dict[str, float]


class LLMRiskConfig(BaseModel):
    cooldown_sec: int = 45
    feature_fingerprint: FeatureFingerprintConfig
    cache: CacheConfig
    distributed: DistributedConfig
    fallback: FallbackConfig


class ProviderConfig(BaseModel):
    enabled: bool = True
    max_items: int = 200
    window_min: int = 90
    trusted_sources: Optional[List[str]] = None
    min_followers: Optional[int] = None


class SanitizerConfig(BaseModel):
    max_chars: int = 2000
    strip_urls: bool = True
    strip_mentions: bool = True


class AggregationConfig(BaseModel):
    sentiment_confidence_threshold: float = 0.65
    severity_confirm_min_sources: int = 2
    severity_levels: List[str] = Field(default_factory=lambda: ["none", "low", "med", "high"])


class NewsConfig(BaseModel):
    providers: Dict[str, ProviderConfig]
    sanitizer: SanitizerConfig
    aggregation: AggregationConfig


class NewsRuleConfig(BaseModel):
    high_event_block: bool = True
    high_event_min_confidence: float = 0.7
    high_event_min_sources: int = 2


class VolatilityRuleConfig(BaseModel):
    atr_pct_downgrade: float = 0.5
    atr_pct_block: float = 0.8
    spread_bps_block: float = 8.0


class TimeWindowsConfig(BaseModel):
    deny: List[str] = Field(default_factory=list)


class CorrelationRuleConfig(BaseModel):
    read_from_cache: bool = True
    block_if_correlated: bool = True
    rho_threshold: float = 0.8
    stale_penalty_multiplier: float = 0.5


class RiskRulesConfig(BaseModel):
    news: NewsRuleConfig
    volatility: VolatilityRuleConfig
    time_windows: TimeWindowsConfig
    correlation: CorrelationRuleConfig


class Settings(BaseModel):
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    llm: LLMConfig
    llm_risk: LLMRiskConfig
    news: NewsConfig
    risk_rules: RiskRulesConfig

    @property
    def prompt_version(self) -> str:
        return "v2.2.0"

    def json_schema_path(self) -> str:
        return self.llm.output_json_schema
