from src.llm.cost_control import BudgetManager
from src.config.models import LLMConfig, LLMStageConfig, LLMReliabilityConfig, AdaptiveBudgetingConfig, EmergencyProviderConfig, DegradationConfig


def _dummy_llm_config() -> LLMConfig:
    return LLMConfig(
        per_mode_budget_usd_per_min={"paper": 0.5},
        token_budget_per_tick=1000,
        max_on_demand_features=3,
        aggregator_tau=1.0,
        stages={"A": LLMStageConfig(provider="deepseek", max_tokens=400, temperature=0.2)},
        reliability=LLMReliabilityConfig(window=200, lambda_=0.7),
        adaptive_budgeting=AdaptiveBudgetingConfig(enabled=True, min_frac=0.6, risk_weight=0.4),
        emergency_provider=EmergencyProviderConfig(),
        degradation=DegradationConfig(),
    )


def test_budget_manager_respects_minimum_fraction() -> None:
    manager = BudgetManager(_dummy_llm_config(), "paper")
    snap = manager.compute_budget(regime="volatile", risk_level=0.9)
    assert snap.effective_budget_usd >= manager.base_budget * manager.config.adaptive_budgeting.min_frac
    snap2 = manager.compute_budget(regime="stable", risk_level=0.0)
    assert snap2.effective_budget_usd <= manager.base_budget
