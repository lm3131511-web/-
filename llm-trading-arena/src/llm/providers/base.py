from __future__ import annotations

import abc
from typing import Any, Dict


class LLMProvider(abc.ABC):
    """Minimal interface for deterministic JSON completions."""

    def __init__(self, name: str) -> None:
        self.name = name

    @abc.abstractmethod
    async def complete_json(
        self,
        *,
        prompt: str,
        schema: Dict[str, Any],
        market_snapshot: Dict[str, float],
    ) -> Dict[str, Any]:
        raise NotImplementedError
