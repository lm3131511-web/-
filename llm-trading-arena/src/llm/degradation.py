from __future__ import annotations

import time
from dataclasses import dataclass

from ..config.models import DegradationConfig


@dataclass
class DegradationState:
    mode: str = "full"
    emergency_since: float | None = None


class DegradationController:
    def __init__(self, config: DegradationConfig) -> None:
        self.config = config
        self.state = DegradationState()

    def update(self, *, uncertainty: float, budget_left_pct: float, now_ts: float | None = None) -> str:
        now = time.time() if now_ts is None else now_ts
        cfg = self.config
        mode = self.state.mode
        if uncertainty >= cfg.u_enter or budget_left_pct <= cfg.budget_enter_pct / 100:
            mode = "emergency"
            if self.state.emergency_since is None:
                self.state.emergency_since = now
        elif mode == "emergency":
            elapsed = 0.0 if self.state.emergency_since is None else now - self.state.emergency_since
            if (
                uncertainty < cfg.u_exit
                and budget_left_pct > cfg.budget_exit_pct / 100
                and elapsed >= cfg.min_emergency_min * 60
            ):
                mode = "full"
                self.state.emergency_since = None
        else:
            if uncertainty >= 0.45 or budget_left_pct <= 0.15:
                mode = "minimal"
            elif uncertainty >= 0.35 or budget_left_pct <= 0.25:
                mode = "reduced"
            else:
                mode = "full"
        self.state.mode = mode
        return mode
