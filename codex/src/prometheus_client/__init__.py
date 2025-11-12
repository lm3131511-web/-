from __future__ import annotations

from typing import Dict


class Metric:
    def __init__(self, name: str, documentation: str, labelnames: tuple[str, ...] = ()) -> None:
        self.name = name
        self.documentation = documentation
        self.labelnames = labelnames
        self.values: Dict[tuple[str, ...], float] = {}

    def labels(self, *values: str):
        key = tuple(values)
        self.values.setdefault(key, 0.0)
        return self

    def inc(self, amount: float = 1.0) -> None:
        for key in list(self.values.keys()):
            self.values[key] += amount

    def observe(self, value: float) -> None:
        self.inc(value)


class Counter(Metric):
    pass


class Histogram(Metric):
    pass
