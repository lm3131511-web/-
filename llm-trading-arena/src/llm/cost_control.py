from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class BudgetState:
    budget_usd_per_min: float
    token_budget_per_tick: int

    def can_spend(self, spent_usd: float) -> bool:
        return spent_usd <= self.budget_usd_per_min


DEFAULT_BUDGET = BudgetState(budget_usd_per_min=1.0, token_budget_per_tick=4000)
