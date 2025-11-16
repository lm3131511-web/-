from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any

from ..contracts.features import DeterministicFeatures
from ..contracts.sentiment import AggregatedSentiment
from ..utils.time import utc_now


@dataclass
class FingerprintState:
    values: Dict[str, Any]
    last_invoked_ts: float


@dataclass
class FingerprintEvaluator:
    deltas: Dict[str, float]
    cooldown_sec: int
    state: FingerprintState | None = None

    def should_invoke(self, features: DeterministicFeatures, sentiment: AggregatedSentiment) -> bool:
        payload = {
            "regime": features.regime,
            "rsi_14": features.rsi_14,
            "atr_pct": features.atr_pct,
            "spread_bps": features.spread_bps,
            "sentiment_score": sentiment.sentiment_score,
            "event_severity": sentiment.event_severity,
        }
        now_ts = utc_now().timestamp()
        if self.state is None:
            self.state = FingerprintState(values=payload, last_invoked_ts=now_ts)
            return True
        if now_ts - self.state.last_invoked_ts < self.cooldown_sec:
            return False
        for key, threshold in self.deltas.items():
            prev = self.state.values.get(key)
            curr = payload.get(key)
            if prev is None or curr is None:
                continue
            if key == "event_severity":
                if prev != curr and threshold <= 1:
                    self.state = FingerprintState(values=payload, last_invoked_ts=now_ts)
                    return True
                continue
            if abs(float(curr) - float(prev)) >= threshold:
                self.state = FingerprintState(values=payload, last_invoked_ts=now_ts)
                return True
        return False

    def update(self, features: DeterministicFeatures, sentiment: AggregatedSentiment) -> None:
        payload = {
            "regime": features.regime,
            "rsi_14": features.rsi_14,
            "atr_pct": features.atr_pct,
            "spread_bps": features.spread_bps,
            "sentiment_score": sentiment.sentiment_score,
            "event_severity": sentiment.event_severity,
        }
        self.state = FingerprintState(values=payload, last_invoked_ts=utc_now().timestamp())
