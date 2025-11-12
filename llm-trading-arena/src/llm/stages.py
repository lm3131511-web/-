from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List

from ..config.models import LLMConfig
from ..core.contracts import AnalystResponse, PriceBandHint, analyst_response_json_schema
from ..monitoring.metrics import GLOBAL_METRICS
from .prompt_loader import build_compound_prompt
from .prompt_vars import render_vars
from .providers import LLMProvider, create_provider


@dataclass(slots=True)
class StageConfig:
    name: str
    provider: LLMProvider
    mode: str
    max_tokens: int
    temperature: float
    prompt_version: str
    limits: Dict[str, Any]
    min_uncertainty: float | None = None
    min_budget_left: float | None = None


class StageRunner:
    def __init__(self, config: StageConfig, token_budget: int) -> None:
        self.config = config
        self.token_budget = token_budget

    async def run(
        self,
        market_snapshot: Dict[str, float],
        *,
        regime: str,
        risk_level: float,
    ) -> AnalystResponse:
        schema = analyst_response_json_schema()
        prompt = self._build_prompt(market_snapshot, regime=regime, risk_level=risk_level, schema=schema)
        prompt_hash = self._prompt_hash(prompt)
        GLOBAL_METRICS.record_prompt(self.config.name, self.config.prompt_version, prompt_hash)

        start = time.perf_counter()
        repaired = False
        try:
            completion = await self.config.provider.complete_json(prompt=prompt, schema=schema)
            meta = self.config.provider.last_completion_meta
            repaired = bool(meta.get("json_repair_used")) or bool(meta.get("mock_fallback_used"))
        except Exception as exc:  # pragma: no cover - defensive guard
            completion = self._fallback_payload(reason=str(exc))
            repaired = True
            meta = {"cost_usd": 0.0}
        latency_ms = (time.perf_counter() - start) * 1000
        GLOBAL_METRICS.record_llm_completion(repaired=repaired)

        prompt_tokens = int(meta.get("prompt_tokens") or max(1, len(prompt) // 4))
        completion_tokens = int(
            meta.get("completion_tokens")
            or max(1, len(json.dumps(completion, ensure_ascii=False)) // 4)
        )
        cost_usd = float(
            meta.get("cost_usd")
            or ((prompt_tokens + completion_tokens) / 1000.0 * 0.002)
        )
        GLOBAL_METRICS.record_llm_usage(
            stage=self.config.name,
            provider=self.config.provider.name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
        )
        price_band_hint = None
        if completion.get("price_band_bps") is not None:
            price_band_hint = PriceBandHint(width_bps=float(completion["price_band_bps"]))

        uncertainty_hints = [str(h) for h in completion.get("uncertainty_hints", [])]
        requested_features = [str(f) for f in completion.get("requested_features", [])]
        ttl_hint = completion.get("ttl_hint_sec")
        ttl_value = int(ttl_hint) if ttl_hint is not None else None
        if ttl_value == 0:
            ttl_value = None

        return AnalystResponse(
            stage=self.config.name,
            provider=self.config.provider.name,
            prompt_version=self.config.prompt_version,
            prompt_hash=prompt_hash,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            direction=completion.get("direction", "FLAT"),
            strategy=completion.get("strategy", "POST_ONLY"),
            confidence=float(completion.get("confidence", 0.0)),
            urgency=float(completion.get("urgency", 0.0)),
            size_hint_frac=float(completion.get("size_hint_frac", 0.0)),
            ttl_hint_sec=ttl_value,
            price_band_hint=price_band_hint,
            uncertainty_hints=uncertainty_hints,
            requested_features=requested_features,
            reliability=float(completion.get("reliability", 0.5)),
            reasoning=completion.get("reasoning"),
        )

    def _build_prompt(
        self,
        market_snapshot: Dict[str, float],
        *,
        regime: str,
        risk_level: float,
        schema: Dict[str, Any],
    ) -> str:
        snapshot_vars = dict(market_snapshot)
        snapshot_vars.setdefault(
            "micro_volatility_q",
            market_snapshot.get("micro_volatility_q", market_snapshot.get("volatility", 0.0)),
        )
        snapshot_vars.setdefault("imbalance", snapshot_vars.get("order_imbalance", 0.0))
        snapshot_vars.setdefault("last_trades_summary", market_snapshot.get("last_trades_summary", "n/a"))
        snapshot_vars.setdefault(
            "on_demand_features_count",
            self._count_on_demand_features(market_snapshot),
        )
        vars_block = render_vars(snapshot_vars, self.config.limits, regime, risk_level)
        return build_compound_prompt(
            stage=self.config.name,
            provider=self.config.provider.name,
            prompt_version=self.config.prompt_version,
            regime=regime,
            variables_text=vars_block,
            schema=schema,
        )

    def _fallback_payload(self, *, reason: str | None = None) -> Dict[str, Any]:
        hints = ["llm_failure"]
        if reason:
            hints.append(reason[:64])
        return {
            "direction": "FLAT",
            "strategy": "POST_ONLY",
            "confidence": 0.0,
            "urgency": 0.0,
            "size_hint_frac": 0.0,
            "ttl_hint_sec": None,
            "uncertainty_hints": hints,
            "requested_features": [],
            "reliability": 0.3,
        }

    @staticmethod
    def _prompt_hash(prompt: str) -> str:
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _count_on_demand_features(snapshot: Dict[str, float]) -> int:
        return sum(1 for key in snapshot if key.startswith("od_"))


def build_stage_runners(config: LLMConfig, *, limits: Dict[str, Any]) -> List[StageRunner]:
    runners: List[StageRunner] = []
    base_limits = dict(limits)
    base_limits.setdefault("max_on_demand_features", config.max_on_demand_features)
    for name, cfg in config.stages.items():
        provider = create_provider(cfg.provider)
        provider.set_mock_mode(config.mock_mode)
        provider.set_run_mode(cfg.mode)
        stage_limits = dict(base_limits)
        stage_limits.setdefault("max_tokens", cfg.max_tokens)
        runners.append(
            StageRunner(
                StageConfig(
                    name=name,
                    provider=provider,
                    mode=cfg.mode,
                    max_tokens=cfg.max_tokens,
                    temperature=cfg.temperature,
                    prompt_version=cfg.prompt_version,
                    limits=stage_limits,
                    min_uncertainty=cfg.min_uncertainty,
                    min_budget_left=cfg.min_budget_left,
                ),
                token_budget=config.token_budget_per_tick,
            )
        )
    return runners
