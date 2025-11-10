from src.llm.aggregator import _uncertainty


def test_uncertainty_bounds_and_sensitivity() -> None:
    low = _uncertainty([0.5, 0.52, 0.48])
    high = _uncertainty([0.1, 0.9, 0.2])
    assert 0.0 <= low <= 1.0
    assert 0.0 <= high <= 1.0
    assert high > low
