from src.config.loader import load_config
from src.llm.cost_control import BudgetManager


def test_provider_budget_guard_blocks_excess() -> None:
    config = load_config("config.sample.yaml")
    config.llm.budget_usd_per_min_per_provider["A"] = 0.0001
    manager = BudgetManager(config.llm, "paper")
    # spend within budget
    assert manager.register_provider_spend("A", 0.00005) is True
    # exceeding cumulative budget trips guard
    assert manager.register_provider_spend("A", 0.0002) is False
