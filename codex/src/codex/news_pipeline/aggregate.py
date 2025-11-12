from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Iterable

from ..config.models import AggregationConfig
from ..contracts.sentiment import SentimentEvent, AggregatedSentiment


def aggregate_sentiment(events: Iterable[SentimentEvent], config: AggregationConfig) -> AggregatedSentiment:
    events = list(events)
    if not events:
        return AggregatedSentiment(
            sentiment_score=0.0,
            event_severity="none",
            confidence=0.0,
            sources_confirmed=0,
        )

    trusted_events = [ev for ev in events if ev.trusted]
    severity_counter = Counter(ev.severity for ev in events)
    severity_levels = config.severity_levels
    severity_rank = {level: idx for idx, level in enumerate(severity_levels)}

    def pick_severity() -> str:
        if not severity_counter:
            return "none"
        ranked = sorted(severity_counter.items(), key=lambda item: severity_rank.get(item[0], -1), reverse=True)
        severity, count = ranked[0]
        if severity == "high" and count < config.severity_confirm_min_sources:
            return "med" if severity_rank.get("med") is not None else "low"
        return severity

    severity = pick_severity()
    confidence = min(1.0, mean(ev.confidence for ev in events))
    if severity == "high" and len(trusted_events) < config.severity_confirm_min_sources:
        severity = "med"
    sentiment_score = mean(ev.sentiment for ev in events)
    if abs(sentiment_score) < config.sentiment_confidence_threshold:
        sentiment_score = 0.0
    return AggregatedSentiment(
        sentiment_score=sentiment_score,
        event_severity=severity,
        confidence=confidence,
        sources_confirmed=len(trusted_events),
    )
