from __future__ import annotations

from typing import Dict, Iterable, List, Tuple


class CollectorRegistry:
    def __init__(self) -> None:
        self._metrics: Dict[str, Metric] = {}

    def register(self, metric: "Metric") -> None:
        self._metrics.setdefault(metric.name, metric)

    def collect(self) -> Iterable["Metric"]:
        return list(self._metrics.values())


REGISTRY = CollectorRegistry()


class Metric:
    metric_type = "counter"

    def __init__(
        self,
        name: str,
        documentation: str,
        labelnames: tuple[str, ...] = (),
        registry: CollectorRegistry | None = None,
        **_: object,
    ) -> None:
        self.name = name
        self.documentation = documentation
        self.labelnames = labelnames
        self.registry = registry or REGISTRY
        self.values: Dict[Tuple[str, ...], float] = {}
        self.registry.register(self)

    def labels(self, *values: str, **label_kwargs: str):
        if label_kwargs:
            ordered = tuple(label_kwargs.get(name, "") for name in self.labelnames)
        else:
            ordered = values
        key = tuple(ordered)
        self.values.setdefault(key, 0.0)
        return _LabelledMetric(self, key)

    def _inc(self, key: Tuple[str, ...], amount: float) -> None:
        self.values[key] = self.values.get(key, 0.0) + amount

    def _observe(self, key: Tuple[str, ...], value: float) -> None:
        self._inc(key, value)

    def total(self) -> float:
        return sum(self.values.values())

    def inc(self, amount: float = 1.0) -> None:
        key: Tuple[str, ...] = tuple()
        self.values.setdefault(key, 0.0)
        self._inc(key, amount)

    def observe(self, value: float) -> None:
        key: Tuple[str, ...] = tuple()
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
    metric_type = "counter"


class Histogram(Metric):
    metric_type = "histogram"

    def __init__(self, *args: object, **kwargs: object) -> None:
        self.observations: Dict[Tuple[str, ...], List[float]] = {}
        super().__init__(*args, **kwargs)

    def _observe(self, key: Tuple[str, ...], value: float) -> None:
        self.observations.setdefault(key, []).append(value)
        super()._observe(key, value)


def _format_labels(metric: Metric, key: Tuple[str, ...]) -> str:
    if not metric.labelnames:
        return ""
    labels = ",".join(f"{name}=\"{value}\"" for name, value in zip(metric.labelnames, key))
    return f"{{{labels}}}"


def generate_latest(registry: CollectorRegistry | None = None) -> bytes:
    reg = registry or REGISTRY
    lines: List[str] = []
    for metric in reg.collect():
        lines.append(f"# HELP {metric.name} {metric.documentation}")
        lines.append(f"# TYPE {metric.name} {metric.metric_type}")
        if metric.values:
            for key, value in metric.values.items():
                label_suffix = _format_labels(metric, key)
                lines.append(f"{metric.name}{label_suffix} {value}")
        else:
            lines.append(f"{metric.name} 0")
    lines.append("")
    return "\n".join(lines).encode("utf-8")


__all__ = [
    "CollectorRegistry",
    "REGISTRY",
    "Counter",
    "Histogram",
    "generate_latest",
]
