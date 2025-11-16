import time

from codex.contracts.verdict import RiskAssessment
from codex.llm_risk.cache import TTLCache


def test_cache_respects_ttl(tmp_path):
    cache = TTLCache[RiskAssessment](ttl_sec=1, max_items=2)
    key = "foo"
    decision = RiskAssessment(
        verdict="CONFIRM",
        size_multiplier=1.0,
        risk_tags=[],
        short_reason="ok",
        prompt_version="v2.2.0",
        cache_hit=False,
        latency_ms=0,
        is_fallback=False,
        stale_correlation=False,
    )
    cache.set(key, decision)
    assert cache.get(key) is not None
    time.sleep(1.1)
    assert cache.get(key) is None
