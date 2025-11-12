from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config.loader import load_settings
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
    config_dir = root / "configs"
    base_path = config_dir / "base.yaml"
    overlay_path = config_dir / f"{env}.yaml" if env else None
    settings = load_settings(base_path, overlay_path if overlay_path and overlay_path.exists() else None)

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
