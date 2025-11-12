from __future__ import annotations

import math


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def logit(p: float, *, eps: float = 1e-6) -> float:
    p = clamp(p, eps, 1.0 - eps)
    return math.log(p / (1 - p))


def inv_logit(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))
