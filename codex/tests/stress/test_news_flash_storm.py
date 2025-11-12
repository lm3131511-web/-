from codex.config.models import AggregationConfig
from codex.contracts.sentiment import SentimentEvent
from codex.news_pipeline.aggregate import aggregate_sentiment


def test_aggregate_large_news_batch():
    config = AggregationConfig(sentiment_confidence_threshold=0.2, severity_confirm_min_sources=2)
    events = [
        SentimentEvent(source=f"src-{i}", severity="med", sentiment=(-1) ** i * 0.5, confidence=0.9, trusted=i % 2 == 0)
        for i in range(200)
    ]
    aggregated = aggregate_sentiment(events, config)
    assert aggregated.sources_confirmed >= 50
    assert aggregated.event_severity in {"med", "high"}
