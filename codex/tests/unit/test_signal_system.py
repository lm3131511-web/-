import os
from pathlib import Path

import asyncio
import pytest

from codex.config.loader import load_settings
from codex.config.models import Settings
from codex.contracts.features import DeterministicFeatures, MetaContext
from codex.contracts.sentiment import AggregatedSentiment
from codex.llm.provider_registry import ProviderRegistry
from codex.llm_risk.client import LLMRiskClient
from codex.llm_risk.providers.base import StubProvider
from codex.signals.llm import MetaJudgeClient, SignalAnalystClient
from codex.signals.system import SignalSystem


class NamedStubProvider(StubProvider):
    def __init__(self, name: str, response: dict):
        super().__init__(response)
        self.name = name


def build_registry(responses: dict[str, dict]) -> ProviderRegistry:
    providers = [NamedStubProvider(name, payload) for name, payload in responses.items()]
    return ProviderRegistry(providers)


@pytest.fixture(scope="module")
def settings() -> Settings:
    os.environ["CODEX_CONFIG_DIR"] = str(Path(__file__).resolve().parents[2] / "configs")
    return load_settings()


def test_signal_pipeline_produces_final_signal(tmp_path, settings):
    features = DeterministicFeatures(regime="trend", rsi_14=65, atr_pct=0.8, spread_bps=3.0)
    sentiment = AggregatedSentiment(sentiment_score=0.4, event_severity="med", confidence=0.8, sources_confirmed=2)
    meta = MetaContext(mode="paper", instrument="XAUUSD", timeframe="M15", last_price=2650.5)

    risk_response = {
        "verdict": "CONFIRM",
        "size_multiplier": 0.85,
        "risk_tags": ["trend_ok"],
        "short_reason": "trend intact",
        "prompt_version": "v2.2.0",
        "cache_hit": False,
        "latency_ms": 120,
        "is_fallback": False,
        "stale_correlation": False,
    }
    risk_registry = build_registry({"qwen": risk_response, "deepseek": risk_response, "claude": risk_response})
    risk_client = LLMRiskClient(settings, registry=risk_registry)

    analyst_payload = {
        "explanation": "Momentum intact",
        "confidence": 0.7,
        "key_drivers": ["RSI>60"],
        "risk_callouts": ["watch spreads"],
        "timeframe_alignment": "intra",
        "recommended_action": "publish",
        "short_summary": "Momentum long remains valid",
    }
    analyst_registry = build_registry({"qwen": analyst_payload, "deepseek": analyst_payload, "claude": analyst_payload})
    analyst_client = SignalAnalystClient(settings, registry=analyst_registry)

    meta_payload = {
        "final_verdict": "CONFIRM",
        "priority": "normal",
        "warnings": [],
        "llm_confidence": 0.66,
        "status_note": "Consensus met",
        "publish": True,
        "annotations": ["consensus_met"],
        "recommended_tags": ["news_risk"],
        "explanation": "Ready to publish",
    }
    meta_registry = build_registry({"qwen": meta_payload, "deepseek": meta_payload, "claude": meta_payload})
    meta_client = MetaJudgeClient(settings, registry=meta_registry)

    system = SignalSystem(
        settings,
        risk_client=risk_client,
        analyst_client=analyst_client,
        meta_client=meta_client,
        signal_log_path=tmp_path / "signals.jsonl",
    )

    signals = asyncio.run(system.generate(features, sentiment, meta))
    assert signals
    final = signals[0]
    assert final.instrument == "XAUUSD"
    assert final.publish is True
    assert "news_risk" in final.risk_tags


def test_meta_judge_requires_consensus(tmp_path, settings):
    features = DeterministicFeatures(regime="trend", rsi_14=60, atr_pct=0.9, spread_bps=4.0)
    sentiment = AggregatedSentiment(sentiment_score=-0.1, event_severity="high", confidence=0.7, sources_confirmed=3)
    meta = MetaContext(mode="live", instrument="ETHUSD", timeframe="M30", last_price=3000.0)

    risk_response = {
        "verdict": "CONFIRM",
        "size_multiplier": 0.75,
        "risk_tags": [],
        "short_reason": "macro ok",
        "prompt_version": "v2.2.0",
        "cache_hit": False,
        "latency_ms": 80,
        "is_fallback": False,
        "stale_correlation": False,
    }
    risk_client = LLMRiskClient(settings, registry=build_registry({"qwen": risk_response, "deepseek": risk_response, "claude": risk_response}))

    analyst_payload = {
        "explanation": "Signal under review",
        "confidence": 0.6,
        "key_drivers": ["macro event"],
        "risk_callouts": ["cpi soon"],
        "timeframe_alignment": "swing",
        "recommended_action": "publish",
        "short_summary": "Signal possible with caution",
    }
    analyst_client = SignalAnalystClient(settings, registry=build_registry({"qwen": analyst_payload, "deepseek": analyst_payload, "claude": analyst_payload}))

    meta_responses = {
        "qwen": {
            "final_verdict": "CONFIRM",
            "priority": "normal",
            "warnings": [],
            "llm_confidence": 0.65,
            "status_note": "ok",
            "publish": True,
            "annotations": ["primary"],
            "recommended_tags": [],
            "explanation": "ready",
        },
        "deepseek": {
            "final_verdict": "BLOCK",
            "priority": "high",
            "warnings": ["macro"],
            "llm_confidence": 0.4,
            "status_note": "block",
            "publish": False,
            "annotations": ["secondary"],
            "recommended_tags": ["llm_disagreement"],
            "explanation": "disagree",
        },
        "claude": {
            "final_verdict": "DOWNGRADE",
            "priority": "normal",
            "warnings": [],
            "llm_confidence": 0.5,
            "status_note": "review",
            "publish": True,
            "annotations": [],
            "recommended_tags": [],
            "explanation": "review",
        },
    }
    meta_client = MetaJudgeClient(settings, registry=build_registry(meta_responses))

    system = SignalSystem(
        settings,
        risk_client=risk_client,
        analyst_client=analyst_client,
        meta_client=meta_client,
        signal_log_path=tmp_path / "signals_consensus.jsonl",
    )

    signals = asyncio.run(system.generate(features, sentiment, meta))
    assert signals
    final = signals[0]
    assert final.publish is False
    assert final.status != "normal"
    assert any(tag == "llm_disagreement" for tag in final.risk_tags)
