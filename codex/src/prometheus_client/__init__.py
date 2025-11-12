from __future__ import annotations

from typing import Dict, List, Tuple


class Metric:
    def __init__(
        self,
        name: str,
        documentation: str,
        labelnames: tuple[str, ...] = (),
        **_: object,
    ) -> None:
        self.name = name
        self.documentation = documentation
        self.labelnames = labelnames
        self.values: Dict[Tuple[str, ...], float] = {}

    def labels(self, *values: str, **label_kwargs: str):
        if label_kwargs:
            ordered = tuple(label_kwargs.get(name, "") for name in self.labelnames)
        else:
            ordered = values
        key = tuple(ordered)
        self.values.setdefault(key, 0.0)
        return _LabelledMetric(self, key)

    def _inc(self, key: Tuple[str, ...], amount: float) -> None:
        self.values[key] += amount

    def _observe(self, key: Tuple[str, ...], value: float) -> None:
        self._inc(key, value)

    def total(self) -> float:
        return sum(self.values.values())

    def inc(self, amount: float = 1.0) -> None:
        key = tuple()
        self.values.setdefault(key, 0.0)
        self._inc(key, amount)

    def observe(self, value: float) -> None:
        key = tuple()
        self.values.setdefault(key, 0.0)
        self._observe(key, value)


class _LabelledMetric:
    def __init__(self, metric: Metric, key: Tuple[str, ...]) -> None:
        self.metric = metric
        self.key = key

    def inc(self, amount: float = 1.0) -> None:
        self.metric._inc(self.key, amount)

    def observe(self, value: float) -> None:
        self.metric._observe(self.key, value)


class Counter(Metric):
    pass


class Histogram(Metric):
    def __init__(self, *args: object, **kwargs: object) -> None:
        self.observations: Dict[Tuple[str, ...], List[float]] = {}
        super().__init__(*args, **kwargs)

    def _observe(self, key: Tuple[str, ...], value: float) -> None:
        self.observations.setdefault(key, []).append(value)
        super()._observe(key, value)
