from __future__ import annotations

from dataclasses import dataclass

from ..config.models import AdaptiveBudgetingConfig, LLMConfig


@dataclass
class BudgetSnapshot:
    effective_budget_usd: float
    base_budget_usd: float
    risk_level: float
    regime: str


class BudgetManager:
    def __init__(self, config: LLMConfig, mode: str) -> None:
        self.config = config
        self.mode = mode
        self.base_budget = config.per_mode_budget_usd_per_min.get(mode, 0.1)
        self.snapshot = BudgetSnapshot(
            effective_budget_usd=self.base_budget,
            base_budget_usd=self.base_budget,
            risk_level=0.0,
            regime="unknown",
        )

    def compute_budget(self, *, regime: str, risk_level: float) -> BudgetSnapshot:
        adaptive = self.config.adaptive_budgeting
        budget = self.base_budget
        if adaptive.enabled:
            frac = max(adaptive.min_frac, 1.0 - adaptive.risk_weight * risk_level)
            budget = max(self.base_budget * adaptive.min_frac, self.base_budget * frac)
        self.snapshot = BudgetSnapshot(
            effective_budget_usd=budget,
            base_budget_usd=self.base_budget,
            risk_level=risk_level,
            regime=regime,
        )
        return self.snapshot
