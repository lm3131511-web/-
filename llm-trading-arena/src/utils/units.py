from __future__ import annotations


def bps(value: float) -> float:
    return value * 10_000.0


def from_bps(value: float) -> float:
    return value / 10_000.0
