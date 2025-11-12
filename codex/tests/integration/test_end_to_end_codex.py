import asyncio

from codex.config.models import Settings
from codex.contracts.features import DeterministicFeatures, MetaContext
from codex.contracts.sentiment import AggregatedSentiment
from codex.llm_risk.client import LLMRiskClient

def test_end_to_end_flow(settings: Settings):
    client = LLMRiskClient(settings)
    features = DeterministicFeatures(regime="normal", rsi_14=45, atr_pct=0.2, spread_bps=3)
    sentiment = AggregatedSentiment(sentiment_score=-0.2, event_severity="low", confidence=0.6, sources_confirmed=2)
    meta = MetaContext(mode="live")
    decision = asyncio.run(client.evaluate(features=features, sentiment=sentiment, meta=meta))
    assert decision.verdict in {"CONFIRM", "DOWNGRADE", "BLOCK"}
    assert decision.prompt_version == "v2.2.0"
