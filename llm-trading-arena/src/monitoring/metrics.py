from __future__ import annotations

import threading
from typing import Any, Dict


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._metrics: Dict[str, float] = {}

    def set_metric(self, name: str, value: float) -> None:
        with self._lock:
            self._metrics[name] = value

    def inc_metric(self, name: str, value: float = 1.0) -> None:
        with self._lock:
            self._metrics[name] = self._metrics.get(name, 0.0) + value

    def snapshot(self) -> Dict[str, float]:
        with self._lock:
            return dict(self._metrics)


GLOBAL_METRICS = MetricsRegistry()
