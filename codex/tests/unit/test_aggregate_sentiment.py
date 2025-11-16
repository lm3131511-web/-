from codex.config.models import AggregationConfig
from codex.config.models import AggregationConfig
from codex.contracts.sentiment import SentimentEvent
from codex.news_pipeline.aggregate import aggregate_sentiment


def test_high_severity_requires_trusted_confirmation():
    config = AggregationConfig(sentiment_confidence_threshold=0.1, severity_confirm_min_sources=2)
    events = [
        SentimentEvent(source="tw", severity="high", sentiment=-0.8, confidence=0.9, trusted=False),
        SentimentEvent(source="news", severity="high", sentiment=-0.7, confidence=0.8, trusted=True),
    ]
    aggregated = aggregate_sentiment(events, config)
    assert aggregated.event_severity == "med"
    assert aggregated.sources_confirmed == 1
