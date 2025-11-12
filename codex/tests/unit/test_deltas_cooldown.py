from datetime import datetime, timezone
from unittest.mock import patch

from codex.contracts.features import DeterministicFeatures
from codex.contracts.sentiment import AggregatedSentiment
from codex.features.deltas import FingerprintEvaluator


@patch("codex.features.deltas.utc_now")
def test_cooldown_prevents_frequent_invocations(mock_now):
    mock_now.side_effect = [
        datetime.fromtimestamp(0, tz=timezone.utc),
        datetime.fromtimestamp(10, tz=timezone.utc),
        datetime.fromtimestamp(50, tz=timezone.utc),
    ]
    evaluator = FingerprintEvaluator(deltas={"rsi_14": 5.0}, cooldown_sec=30)
    features = DeterministicFeatures(regime="normal", rsi_14=50, atr_pct=0.4, spread_bps=5)
    sentiment = AggregatedSentiment(sentiment_score=0.0, event_severity="none", confidence=0.1, sources_confirmed=0)
    assert evaluator.should_invoke(features, sentiment)
    features.rsi_14 = 54.0
    assert not evaluator.should_invoke(features, sentiment)
    features.rsi_14 = 56.0
    assert evaluator.should_invoke(features, sentiment)
