from src.llm.degradation import DegradationController
from src.config.models import DegradationConfig


def test_degradation_escalates_and_exits() -> None:
    controller = DegradationController(DegradationConfig())
    mode = controller.update(uncertainty=0.2, budget_left_pct=0.5)
    assert mode == "full"
    mode = controller.update(uncertainty=0.6, budget_left_pct=0.1)
    assert mode == "emergency"
    # insufficient time elapsed to exit
    mode = controller.update(uncertainty=0.1, budget_left_pct=0.5, now_ts=controller.state.emergency_since + 100)
    assert mode == "emergency"
    # force exit after min emergency window
    exit_time = controller.state.emergency_since + DegradationConfig().min_emergency_min * 60 + 1
    mode = controller.update(uncertainty=0.1, budget_left_pct=0.5, now_ts=exit_time)
    assert mode == "full"
