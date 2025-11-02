from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List

from ..core.contracts import AnalystResponse


@dataclass(slots=True)
class StageConfig:
    name: str
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
        confidence = max(0.0, min(1.0, 0.5 + random.uniform(-0.1, 0.1)))
        reasoning = f"Stage {self.config.name} processed snapshot"
        decision = random.choice(["BUY", "SELL", "HOLD"])
        return AnalystResponse(
            stage=self.config.name,
            prompt_tokens=int(self.config.max_tokens * 0.6),
            completion_tokens=int(self.config.max_tokens * 0.1),
            latency_ms=(time.perf_counter() - start) * 1000,
            decision_confidence=confidence,
            recommended_action=decision,
            reasoning=reasoning,
            metadata={"budget_left_tokens": max(0, self.token_budget - self.config.max_tokens)},
            features=list(sorted(market_snapshot.keys()))[:5],
        )


def build_stage_runners(configs: Dict[str, Dict[str, float]], token_budget: int) -> List[StageRunner]:
    runners: List[StageRunner] = []
    for name, cfg in configs.items():
        runners.append(
            StageRunner(
                StageConfig(
                    name=name,
                    max_tokens=int(cfg.get("max_tokens", token_budget // 3)),
                    temperature=float(cfg.get("temperature", 0.2)),
                    min_uncertainty=cfg.get("min_uncertainty"),
                    min_budget_left=cfg.get("min_budget_left"),
                ),
                token_budget=token_budget,
            )
        )
    return runners
