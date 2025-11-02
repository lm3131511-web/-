from __future__ import annotations

from dataclasses import dataclass
from typing import Deque
from collections import deque


@dataclass
class CircuitBreakerState:
    history: Deque[float]
    tripped: bool = False


class CalibrationCircuitBreaker:
    def __init__(self, window: int, threshold: float) -> None:
        self.state = CircuitBreakerState(history=deque(maxlen=window))
        self.threshold = threshold

    def update(self, ece: float) -> bool:
        self.state.history.append(ece)
        if len(self.state.history) == self.state.history.maxlen and sum(self.state.history) / len(
            self.state.history
        ) > self.threshold:
            self.state.tripped = True
        return self.state.tripped

    def reset(self) -> None:
        self.state.history.clear()
        self.state.tripped = False
