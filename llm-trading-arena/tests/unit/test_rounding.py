from __future__ import annotations

import pytest

from src.exec.rounding import PrecisionSpec, RoundingError, format_price, format_qty, validate_and_round


def test_validate_and_round_enforces_min_notional() -> None:
    spec = PrecisionSpec(step_size=0.01, tick_size=0.1, min_qty=0.05, min_notional=10)
    qty, price = validate_and_round(0.1, 101.23, spec)
    assert qty == format_qty(0.1, spec.step_size)
    assert price == format_price(101.2, spec.tick_size)


def test_validate_and_round_raises_when_impossible() -> None:
    spec = PrecisionSpec(step_size=5, tick_size=1, min_qty=5, min_notional=100)
    with pytest.raises(RoundingError):
        validate_and_round(0.1, 10, spec)
