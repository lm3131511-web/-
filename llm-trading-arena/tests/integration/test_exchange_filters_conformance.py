import pytest

from src.exec.rounding import PrecisionSpec, RoundingError, validate_and_round


def test_validate_and_round_enforces_min_notional() -> None:
    spec = PrecisionSpec(step_size=0.001, tick_size=0.01, min_qty=0.001, min_notional=10.0)
    qty, price = validate_and_round(qty=0.01, price=1000.0, spec=spec)
    assert float(qty) * float(price) >= spec.min_notional
    with pytest.raises(RoundingError):
        validate_and_round(qty=0.0001, price=10.0, spec=spec)
