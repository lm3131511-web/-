from __future__ import annotations

from typing import Dict, Type

from .base import LLMProvider
from .claude import ClaudeProvider
from .deepseek import DeepSeekProvider
from .qwen import QwenProvider

_PROVIDER_FACTORIES: Dict[str, Type[LLMProvider]] = {
    "deepseek": DeepSeekProvider,
    "qwen": QwenProvider,
    "claude": ClaudeProvider,
}


def create_provider(name: str) -> LLMProvider:
    try:
        factory = _PROVIDER_FACTORIES[name]
    except KeyError as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"unknown provider: {name}") from exc
    return factory()


__all__ = ["LLMProvider", "create_provider"]
