from __future__ import annotations

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Dict, List

from ..config.models import LLMConfig
from ..core.contracts import AnalystResponse, PriceBandHint
from .providers import LLMProvider, load_providers


@dataclass(slots=True)
class StageConfig:
    name: str
    provider: LLMProvider
    max_tokens: int
    temperature: float
    prompt_version: str = "v1"
    min_uncertainty: float | None = None
    min_budget_left: float | None = None


class StageRunner:
    def __init__(self, config: StageConfig, token_budget: int) -> None:
        self.config = config
        self.token_budget = token_budget

    async def run(self, market_snapshot: Dict[str, float]) -> AnalystResponse:
        prompt = self._build_prompt(market_snapshot)
        schema = self._response_schema()
        start = time.perf_counter()
        completion = await self.config.provider.complete_json(
            prompt=prompt,
            schema=schema,
            market_snapshot=market_snapshot,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        price_band_hint = None
        if completion.get("price_band_bps") is not None:
            price_band_hint = PriceBandHint(width_bps=float(completion["price_band_bps"]))
        return AnalystResponse(
            stage=self.config.name,
            provider=self.config.provider.name,
            prompt_version=self.config.prompt_version,
            prompt_hash=self._prompt_hash(prompt),
            prompt_tokens=int(self.config.max_tokens * 0.6),
            completion_tokens=int(self.config.max_tokens * 0.2),
            latency_ms=latency_ms,
            direction=completion["direction"],
            strategy=completion["strategy"],
            confidence=float(completion["confidence"]),
            urgency=float(completion["urgency"]),
            size_hint_frac=float(completion["size_hint_frac"]),
            ttl_hint_sec=int(completion.get("ttl_hint_sec", 0)) or None,
            price_band_hint=price_band_hint,
            uncertainty_hints=list(completion.get("uncertainty_hints", [])),
            requested_features=list(completion.get("requested_features", [])),
            reliability=float(completion.get("reliability", 0.5)),
            reasoning=completion.get("reasoning"),
        )

    def _build_prompt(self, market_snapshot: Dict[str, float]) -> str:
        regime = market_snapshot.get("regime", "unknown")
        features = ", ".join(f"{k}={v:.4f}" for k, v in sorted(market_snapshot.items()) if isinstance(v, float))
        return (
            f"Stage={self.config.name} provider={self.config.provider.name} temp={self.config.temperature} "
            f"regime={regime} features={features}"
        )

    def _response_schema(self) -> Dict[str, object]:
        return {
            "type": "object",
            "properties": {
                "direction": {"enum": ["BUY", "SELL", "FLAT"]},
                "strategy": {"enum": ["POST_ONLY", "IOC", "POV", "TWAP"]},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "urgency": {"type": "number", "minimum": 0, "maximum": 1},
                "size_hint_frac": {"type": "number", "minimum": 0},
                "ttl_hint_sec": {"type": "integer", "minimum": 0},
                "price_band_bps": {"type": "number", "minimum": 0},
                "uncertainty_hints": {"type": "array", "items": {"type": "string"}},
                "reliability": {"type": "number", "minimum": 0, "maximum": 1},
                "requested_features": {"type": "array", "items": {"type": "string"}},
                "reasoning": {"type": "string"},
            },
            "required": ["direction", "strategy", "confidence", "urgency", "size_hint_frac"],
        }

    @staticmethod
    def _prompt_hash(prompt: str) -> str:
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


def build_stage_runners(config: LLMConfig) -> List[StageRunner]:
    providers = load_providers()
    runners: List[StageRunner] = []
    for name, cfg in config.stages.items():
        provider = providers[cfg.provider]
        runners.append(
            StageRunner(
                StageConfig(
                    name=name,
                    provider=provider,
                    max_tokens=cfg.max_tokens,
                    temperature=cfg.temperature,
                    prompt_version="v1",
                    min_uncertainty=cfg.min_uncertainty,
                    min_budget_left=cfg.min_budget_left,
                ),
                token_budget=config.token_budget_per_tick,
            )
        )
    return runners
