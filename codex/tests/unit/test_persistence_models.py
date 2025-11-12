from codex.contracts.sentiment import AggregatedSentiment
from codex.persistence.models import DecisionRecord, NewsIngestRecord


def test_decision_record_serialises_to_json():
    record = DecisionRecord(
        prompt_version="v2.2.0",
        verdict="CONFIRM",
        size_multiplier=1.0,
        risk_tags=["volatility_spike"],
        cache_hit=False,
        latency_ms=12,
        fingerprint_hash="abc123",
        is_fallback=False,
    )
    payload = record.model_dump()
    assert payload["prompt_version"] == "v2.2.0"
    assert "timestamp" in payload


def test_news_ingest_record_contains_items():
    aggregated = AggregatedSentiment(
        sentiment_score=0.3,
        event_severity="med",
        confidence=0.8,
        sources_confirmed=2,
    )
    record = NewsIngestRecord(aggregated=aggregated, provider_counts={"twitter": 2}, items=[{"id": "1"}])
    payload = record.model_dump()
    assert payload["aggregated"]["event_severity"] == "med"
    assert payload["provider_counts"] == {"twitter": 2}
    assert payload["items"] == [{"id": "1"}]
