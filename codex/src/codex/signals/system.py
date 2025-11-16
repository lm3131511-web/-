from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List

from ..config.models import Settings
from ..contracts.features import DeterministicFeatures, MetaContext
from ..contracts.sentiment import AggregatedSentiment
from ..contracts.verdict import RiskAssessment
from ..llm_risk.client import LLMRiskClient
from ..monitoring.metrics import (
    signal_consensus_counter,
    signals_generated_counter,
    signals_published_counter,
)
from .llm import MetaJudgeClient, SignalAnalystClient
from .models import FinalSignal
from .strategies import SignalStrategyEngine


class SignalSystem:
    def __init__(
        self,
        settings: Settings,
        *,
        risk_client: LLMRiskClient | None = None,
        analyst_client: SignalAnalystClient | None = None,
        meta_client: MetaJudgeClient | None = None,
        signal_log_path: Path | None = None,
    ) -> None:
        self.settings = settings
        self.strategy_engine = SignalStrategyEngine(settings.signal_system.strategies)
        self.risk_client = risk_client or LLMRiskClient(settings)
        self.analyst_client = analyst_client or SignalAnalystClient(settings)
        self.meta_client = meta_client or MetaJudgeClient(settings)
        root = Path(signal_log_path or Path("data/logs/signals.jsonl"))
        root.parent.mkdir(parents=True, exist_ok=True)
        self.signal_log_path = root

    async def generate(
        self,
        features: DeterministicFeatures,
        sentiment: AggregatedSentiment,
        meta: MetaContext,
    ) -> List[FinalSignal]:
        candidates = self.strategy_engine.generate(features, sentiment, meta)
        final_signals: List[FinalSignal] = []
        for candidate in candidates:
            signals_generated_counter.labels(strategy=candidate.strategy).inc()
            risk_assessment = await self.risk_client.evaluate(features=features, sentiment=sentiment, meta=meta)
            explanation = await self.analyst_client.explain(candidate, risk_assessment, sentiment, meta)
            meta_decision = await self.meta_client.judge(candidate, risk_assessment, explanation, sentiment, meta)
            final_signal = FinalSignal.from_components(
                candidate=candidate,
                risk_verdict=risk_assessment.verdict,
                risk_tags=risk_assessment.risk_tags,
                risk_reason=risk_assessment.short_reason,
                meta_decision=meta_decision,
                explanation=explanation,
            )
            signal_consensus_counter.labels(result=meta_decision.final_verdict).inc()
            status_label = final_signal.status if final_signal.publish else "blocked"
            signals_published_counter.labels(status=status_label).inc()
            final_signals.append(final_signal)
            self._log_signal(final_signal, risk_assessment)
        return final_signals

    def _log_signal(self, signal: FinalSignal, risk: RiskAssessment) -> None:
        record = {
            "created_at": signal.created_at,
            "valid_until": signal.valid_until,
            "signal": signal.model_dump(),
            "risk": risk.model_dump(),
        }
        with self.signal_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, default=_json_default, ensure_ascii=False) + "\n")


def _json_default(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    return value
