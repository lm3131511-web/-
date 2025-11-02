from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List

from ..core.contracts import AnalystResponse, PriceBandHint
from .providers import LLMProvider, load_providers


@dataclass(slots=True)
class StageConfig:
    name: str
    provider: LLMProvider
    max_tokens: int
    temperature: float
    min_uncertainty: float | None = None
    min_budget_left: float | None = None


class StageRunner:
    def __init__(self, config: StageConfig, token_budget: int) -> None:
        self.config = config
        self.token_budget = token_budget

    async def run(self, market_snapshot: Dict[str, float]) -> AnalystResponse:
        start = time.perf_counter()
        await asyncio.sleep(0)
        schema = {
            "type": "object",
            "properties": {
                "direction": {"enum": ["BUY", "SELL", "FLAT"]},
                "strategy": {"enum": ["POST_ONLY", "IOC", "POV", "TWAP"]},
                "confidence": {"type": "number"},
                "urgency": {"type": "number"},
                "size_hint_frac": {"type": "number"},
                "ttl_hint_sec": {"type": "integer", "minimum": 0},
                "price_band_bps": {"type": "number"},
                "uncertainty_hints": {"type": "array", "items": {"type": "string"}},
                "reliability": {"type": "number"},
                "reasoning": {"type": "string"},
            },
        }
        completion = await self.config.provider.complete_json(
            prompt=f"stage={self.config.name} temp={self.config.temperature}",
            schema=schema,
            market_snapshot=market_snapshot,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        price_band_hint = None
        if completion.get("price_band_bps") is not None:
            price_band_hint = PriceBandHint(width_bps=float(completion["price_band_bps"]))
        requested_features = completion.get("requested_features", [])
        return AnalystResponse(
            stage=self.config.name,
            provider=self.config.provider.name,
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
            requested_features=list(requested_features),
            reliability=float(completion.get("reliability", 0.5)),
            reasoning=completion.get("reasoning"),
        )


def build_stage_runners(
    configs: Dict[str, Dict[str, float | str]],
    token_budget: int,
) -> List[StageRunner]:
    providers = load_providers()
    runners: List[StageRunner] = []
    for name, cfg in configs.items():
        provider_name = str(cfg["provider"])
        provider = providers[provider_name]
        runners.append(
            StageRunner(
                StageConfig(
                    name=name,
                    provider=provider,
                    max_tokens=int(cfg.get("max_tokens", token_budget // 3)),
                    temperature=float(cfg.get("temperature", 0.2)),
                    min_uncertainty=float(cfg.get("min_uncertainty"))
                    if cfg.get("min_uncertainty") is not None
                    else None,
                    min_budget_left=float(cfg.get("min_budget_left"))
                    if cfg.get("min_budget_left") is not None
                    else None,
                ),
                token_budget=token_budget,
            )
        )
    return runners
