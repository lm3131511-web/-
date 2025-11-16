from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..config.models import RiskRulesConfig
from ..contracts.features import DeterministicFeatures
from ..contracts.sentiment import AggregatedSentiment
from ..contracts.verdict import RiskAssessment
from ..utils.time import utc_now, is_within_window


@dataclass
class RuleResult:
    verdict: str
    size_multiplier: float
    risk_tags: List[str]
    reason: str
    stale_correlation: bool = False


def evaluate_rules(
    *,
    config: RiskRulesConfig,
    features: DeterministicFeatures,
    sentiment: AggregatedSentiment,
) -> RuleResult | None:
    now = utc_now()
    vol_cfg = config.volatility
    if features.atr_pct >= vol_cfg.atr_pct_block or features.spread_bps >= vol_cfg.spread_bps_block:
        return RuleResult(
            verdict="BLOCK",
            size_multiplier=0.0,
            risk_tags=["volatility_spike" if features.atr_pct >= vol_cfg.atr_pct_block else "low_liquidity"],
            reason="volatility gate tripped",
        )
    if features.atr_pct >= vol_cfg.atr_pct_downgrade:
        return RuleResult(
            verdict="DOWNGRADE",
            size_multiplier=0.5,
            risk_tags=["volatility_spike"],
            reason="atr downgrade",
        )
    news_cfg = config.news
    if (
        sentiment.event_severity == "high"
        and sentiment.confidence >= news_cfg.high_event_min_confidence
        and sentiment.sources_confirmed >= news_cfg.high_event_min_sources
    ):
        return RuleResult(
            verdict="BLOCK" if news_cfg.high_event_block else "DOWNGRADE",
            size_multiplier=0.0 if news_cfg.high_event_block else 0.4,
            risk_tags=["news_risk"],
            reason="high severity news",
        )
    for window in config.time_windows.deny:
        if is_within_window(now, window):
            return RuleResult(
                verdict="BLOCK",
                size_multiplier=0.0,
                risk_tags=["low_liquidity"],
                reason="deny window",
            )
    corr_cfg = config.correlation
    stale = False
    if features.correlation_rho is not None:
        if features.correlation_rho >= corr_cfg.rho_threshold:
            mult = 0.0 if corr_cfg.block_if_correlated else 0.5
            return RuleResult(
                verdict="BLOCK" if corr_cfg.block_if_correlated else "DOWNGRADE",
                size_multiplier=mult,
                risk_tags=["correlation_risk"],
                reason="correlation threshold",
            )
    if features.correlation_ts_seconds:
        age = utc_now().timestamp() - features.correlation_ts_seconds
        if age > 900:  # 15 minutes stale
            stale = True
    if stale:
        return RuleResult(
            verdict="DOWNGRADE",
            size_multiplier=corr_cfg.stale_penalty_multiplier,
            risk_tags=["stale_correlation"],
            reason="stale correlation",
            stale_correlation=True,
        )
    return None
