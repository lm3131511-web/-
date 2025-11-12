from __future__ import annotations

import math
from dataclasses import dataclass


class RoundingError(ValueError):
    pass


@dataclass(slots=True)
class PrecisionSpec:
    step_size: float
    tick_size: float
    min_qty: float
    min_notional: float


def _quantize(value: float, step: float, mode: str = "round") -> float:
    if step <= 0:
        return value
    units = value / step
    if mode == "ceil":
        units = math.ceil(units - 1e-12)
    else:
        units = round(units)
    return units * step


def format_price(price: float, tick_size: float) -> str:
    decimals = max(0, -int(round(math.log10(tick_size)))) if tick_size < 1 else 0
    quantized = _quantize(price, tick_size)
    return f"{quantized:.{decimals}f}"


def format_qty(qty: float, step_size: float) -> str:
    decimals = max(0, -int(round(math.log10(step_size)))) if step_size < 1 else 0
    quantized = _quantize(qty, step_size)
    return f"{quantized:.{decimals}f}"


def validate_and_round(
    qty: float,
    price: float,
    spec: PrecisionSpec,
) -> tuple[str, str]:
    q = _quantize(qty, spec.step_size)
    p = _quantize(price, spec.tick_size)
    if q <= 0 or p <= 0:
        raise RoundingError("non-positive")
    notional = q * p
    if notional < spec.min_notional:
        needed = spec.min_notional / p
        q = _quantize(needed, spec.step_size, mode="ceil")
        notional = q * p
    if q < spec.min_qty or notional < spec.min_notional:
        raise RoundingError("cannot satisfy precision constraints")
    return format_qty(q, spec.step_size), format_price(p, spec.tick_size)
