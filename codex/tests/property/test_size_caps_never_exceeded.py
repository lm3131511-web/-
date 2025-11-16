from hypothesis import given, strategies as st

from codex.contracts.verdict import RiskAssessment


@given(st.floats(min_value=0, max_value=2))
def test_size_multiplier_capped(value):
    assessment = RiskAssessment(
        verdict="CONFIRM",
        size_multiplier=min(1.0, value),
        risk_tags=[],
        short_reason="",
        prompt_version="v2.2.0",
        cache_hit=False,
        latency_ms=0,
        is_fallback=False,
        stale_correlation=False,
    )
    assert 0.0 <= assessment.size_multiplier <= 1.0
