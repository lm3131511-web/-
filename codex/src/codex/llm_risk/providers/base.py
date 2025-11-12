from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class LLMProvider(ABC):
    name: str

    @abstractmethod
    async def complete(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Return a structured verdict ready for validation."""


class StubProvider(LLMProvider):
    name = "stub"

    def __init__(self, response: Dict[str, Any]) -> None:
        self._response = response

    async def complete(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._response
