from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Tuple

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
        mode_budget = config.per_mode_budget_usd_per_min.get(mode, config.budget_usd_per_min)
        if config.budget_usd_per_min > 0:
            mode_budget = min(mode_budget, config.budget_usd_per_min)
        self.base_budget = mode_budget
        self.snapshot = BudgetSnapshot(
            effective_budget_usd=self.base_budget,
            base_budget_usd=self.base_budget,
            risk_level=0.0,
            regime="unknown",
        )
        self.provider_budgets: Dict[str, float] = {
            key.upper(): value for key, value in config.budget_usd_per_min_per_provider.items()
        }
        self._provider_usage: Dict[str, Tuple[float, float]] = {}
        self._provider_window_sec = 60.0

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

    def register_provider_spend(
        self, provider: str, cost_usd: float, *, now: float | None = None
    ) -> bool:
        if cost_usd <= 0:
            return True
        key = provider.upper()
        limit = self.provider_budgets.get(key)
        now_ts = time.monotonic() if now is None else now
        window_start, spent = self._provider_usage.get(key, (now_ts, 0.0))
        if now_ts - window_start >= self._provider_window_sec:
            window_start, spent = now_ts, 0.0
        spent += cost_usd
        self._provider_usage[key] = (window_start, spent)
        if not limit or limit <= 0:
            return True
        return spent <= limit
