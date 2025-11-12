from codex.config.loader import load_settings
from codex.config.models import Settings
from codex.contracts.features import DeterministicFeatures
from codex.contracts.sentiment import AggregatedSentiment
from codex.decision.rules import evaluate_rules


def test_volatility_block(settings: Settings):
    features = DeterministicFeatures(regime="normal", rsi_14=40, atr_pct=1.0, spread_bps=2)
    sentiment = AggregatedSentiment(sentiment_score=0.0, event_severity="none", confidence=0.1, sources_confirmed=0)
    result = evaluate_rules(config=settings.risk_rules, features=features, sentiment=sentiment)
    assert result is not None
    assert result.verdict == "BLOCK"
    assert "volatility_spike" in result.risk_tags


def test_news_gate_requires_confidence(settings: Settings):
    sentiment = AggregatedSentiment(sentiment_score=-0.8, event_severity="high", confidence=0.8, sources_confirmed=2)
    features = DeterministicFeatures(regime="normal", rsi_14=40, atr_pct=0.2, spread_bps=2)
    result = evaluate_rules(config=settings.risk_rules, features=features, sentiment=sentiment)
    assert result is not None
    assert result.verdict == "BLOCK"
    assert "news_risk" in result.risk_tags
