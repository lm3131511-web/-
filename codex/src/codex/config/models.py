from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


class RetryConfig(BaseModel):
    max: int = Field(ge=0, default=1)
    backoff_ms: int = Field(ge=0, default=250)


class LLMConfig(BaseModel):
    primary: str
    timeout_ms: int = Field(ge=0, default=2500)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    max_ctx_tokens: int = Field(ge=0, default=32000)
    output_json_schema: str
    fallback_chain: List[str] = Field(default_factory=list)


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


class LLMProviderConfig(BaseModel):
    base_url: str
    api_key_env: str
    model: str
    compatible_mode: bool = True
    api_version: Optional[str] = None
    max_output_tokens: Optional[int] = None


class TrendFollowStrategyConfig(BaseModel):
    timeframe: str = "M15"
    min_rsi: float = 55.0
    max_spread_bps: float = 8.0
    atr_stop_multiple: float = 1.2
    atr_target_multiple: float = 2.0


class MeanReversionStrategyConfig(BaseModel):
    timeframe: str = "M30"
    oversold: float = 30.0
    overbought: float = 70.0
    atr_stop_multiple: float = 1.0
    atr_target_multiple: float = 1.5


class SignalStrategiesConfig(BaseModel):
    trend_follow: TrendFollowStrategyConfig = Field(default_factory=TrendFollowStrategyConfig)
    mean_reversion: MeanReversionStrategyConfig = Field(default_factory=MeanReversionStrategyConfig)


class PromptContractConfig(BaseModel):
    prompt: str
    schema: str
    version: str = "v1.0.0"


class ConsensusPolicyConfig(BaseModel):
    critical_event_severity: str = "high"
    min_agree: int = 2


class SignalSystemConfig(BaseModel):
    analyst: PromptContractConfig
    meta_judge: PromptContractConfig
    strategies: SignalStrategiesConfig = Field(default_factory=SignalStrategiesConfig)
    consensus: ConsensusPolicyConfig = Field(default_factory=ConsensusPolicyConfig)


class Settings(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    llm: LLMConfig
    llm_risk: LLMRiskConfig
    news: NewsConfig
    risk_rules: RiskRulesConfig
    signal_system: SignalSystemConfig
    llm_providers: Dict[str, LLMProviderConfig] = Field(alias="providers")

    @property
    def prompt_version(self) -> str:
        return "v2.2.0"

    def json_schema_path(self) -> Path:
        schema_path = Path(self.llm.output_json_schema)
        if not schema_path.is_absolute():
            root = Path(__file__).resolve().parents[3]
            schema_path = root / schema_path
        return schema_path

    def prompt_path(self) -> Path:
        root = Path(__file__).resolve().parents[3]
        filename = f"system_risk_{self.prompt_version}.md"
        return root / "prompts" / filename

    def analyst_prompt_path(self) -> Path:
        return self._resolve_prompt_path(self.signal_system.analyst.prompt)

    def analyst_schema_path(self) -> Path:
        return self._resolve_prompt_path(self.signal_system.analyst.schema)

    def meta_judge_prompt_path(self) -> Path:
        return self._resolve_prompt_path(self.signal_system.meta_judge.prompt)

    def meta_judge_schema_path(self) -> Path:
        return self._resolve_prompt_path(self.signal_system.meta_judge.schema)

    @staticmethod
    def _resolve_prompt_path(relative: str) -> Path:
        path = Path(relative)
        if path.is_absolute():
            return path
        root = Path(__file__).resolve().parents[3]
        return root / relative

    def get_llm_provider(self, name: str) -> LLMProviderConfig:
        if name not in self.llm_providers:
            raise KeyError(f"LLM provider '{name}' is not configured")
        return self.llm_providers[name]
