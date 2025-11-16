from __future__ import annotations

from typing import List

from ..contracts.features import DeterministicFeatures, MetaContext
from ..contracts.sentiment import AggregatedSentiment
from ..config.models import SignalStrategiesConfig
from ..utils.time import utc_now
from .models import SignalCandidate


class SignalStrategyEngine:
    def __init__(self, config: SignalStrategiesConfig) -> None:
        self.config = config

    def generate(
        self,
        features: DeterministicFeatures,
        sentiment: AggregatedSentiment,
        meta: MetaContext,
    ) -> List[SignalCandidate]:
        price = meta.last_price or 1.0
        price = max(price, 1e-6)
        candidates: List[SignalCandidate] = []
        candidates.extend(self._trend_follow(features, sentiment, meta, price))
        candidates.extend(self._mean_reversion(features, sentiment, meta, price))
        return candidates

    def _trend_follow(
        self,
        features: DeterministicFeatures,
        sentiment: AggregatedSentiment,
        meta: MetaContext,
        price: float,
    ) -> List[SignalCandidate]:
        cfg = self.config.trend_follow
        if features.rsi_14 < cfg.min_rsi or features.spread_bps > cfg.max_spread_bps:
            return []
        atr = max(features.atr_pct / 100.0 * price, price * 0.001)
        stop = price - atr * cfg.atr_stop_multiple
        take = price + atr * cfg.atr_target_multiple
        confidence = min(1.0, (features.rsi_14 - cfg.min_rsi) / 20 + sentiment.confidence * 0.2 + 0.5)
        return [
            SignalCandidate(
                instrument=meta.instrument,
                timeframe=cfg.timeframe or meta.timeframe,
                side="buy",
                entry_price=price,
                stop_loss=max(stop, price * 0.2),
                take_profit=max(take, price * 0.21),
                strategy="trend_follow",
                strategy_confidence=round(confidence, 3),
                features={
                    "rsi_14": features.rsi_14,
                    "atr_pct": features.atr_pct,
                    "spread_bps": features.spread_bps,
                },
                sentiment=sentiment,
                created_at=utc_now(),
            )
        ]

    def _mean_reversion(
        self,
        features: DeterministicFeatures,
        sentiment: AggregatedSentiment,
        meta: MetaContext,
        price: float,
    ) -> List[SignalCandidate]:
        cfg = self.config.mean_reversion
        atr = max(features.atr_pct / 100.0 * price, price * 0.001)
        candidates: List[SignalCandidate] = []
        if features.rsi_14 <= cfg.oversold:
            stop = price - atr * cfg.atr_stop_multiple
            take = price + atr * cfg.atr_target_multiple
            confidence = min(1.0, (cfg.oversold - features.rsi_14) / 20 + 0.4)
            candidates.append(
                SignalCandidate(
                    instrument=meta.instrument,
                    timeframe=cfg.timeframe or meta.timeframe,
                    side="buy",
                    entry_price=price,
                    stop_loss=max(stop, price * 0.2),
                    take_profit=max(take, price * 0.21),
                    strategy="mean_reversion",
                    strategy_confidence=round(confidence, 3),
                    features={
                        "rsi_14": features.rsi_14,
                        "atr_pct": features.atr_pct,
                        "spread_bps": features.spread_bps,
                    },
                    sentiment=sentiment,
                    created_at=utc_now(),
                )
            )
        if features.rsi_14 >= cfg.overbought:
            stop = price + atr * cfg.atr_stop_multiple
            take = price - atr * cfg.atr_target_multiple
            confidence = min(1.0, (features.rsi_14 - cfg.overbought) / 20 + 0.4)
            candidates.append(
                SignalCandidate(
                    instrument=meta.instrument,
                    timeframe=cfg.timeframe or meta.timeframe,
                    side="sell",
                    entry_price=price,
                    stop_loss=max(stop, price * 0.2),
                    take_profit=max(take, price * 0.21),
                    strategy="mean_reversion",
                    strategy_confidence=round(confidence, 3),
                    features={
                        "rsi_14": features.rsi_14,
                        "atr_pct": features.atr_pct,
                        "spread_bps": features.spread_bps,
                    },
                    sentiment=sentiment,
                    created_at=utc_now(),
                )
            )
        return candidates
