from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config.loader import load_settings, resolve_config_path
from .config.models import Settings
from .llm_risk.cache_persist import SQLiteCachePersistor
from .llm_risk.client import LLMRiskClient
from .persistence.store import DecisionLog
from .utils.time import utc_now


@dataclass
class BootstrapState:
    settings: Settings
    llm_client: LLMRiskClient
    decision_log: DecisionLog
    persistor: SQLiteCachePersistor


def bootstrap(env: str | None = None) -> BootstrapState:
    root = Path(__file__).resolve().parents[2]
    overlay_path = None
    if env:
        candidate = resolve_config_path(f"{env}.yaml")
        if candidate.is_file():
            overlay_path = candidate
    settings = load_settings(overlay=overlay_path)

    cache_path = root / settings.llm_risk.cache.persistence.path
    persistor = SQLiteCachePersistor(str(cache_path))
    persistor.prune_expired(utc_now().timestamp())

    decisions_path = root / "data" / "logs" / "decisions.jsonl"
    decision_log = DecisionLog(str(decisions_path))
    client = LLMRiskClient(settings, persistor=persistor, decision_log=decision_log)

    if settings.runtime.cold_start:
        _perform_cold_start()

    return BootstrapState(settings=settings, llm_client=client, decision_log=decision_log, persistor=persistor)


def _perform_cold_start() -> None:
    # Placeholder for correlation pre-computation hooks.
    pass
