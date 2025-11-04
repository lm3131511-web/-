from __future__ import annotations

from typing import Dict

from .base import LLMProvider
from .claude import ClaudeProvider
from .deepseek import DeepSeekProvider
from .qwen import QwenProvider


def load_providers(mock_mode: bool = False) -> Dict[str, LLMProvider]:
    providers: Dict[str, LLMProvider] = {}
    for provider in (DeepSeekProvider(), QwenProvider(), ClaudeProvider()):
        provider.set_mock_mode(mock_mode)
        providers[provider.name] = provider
    return providers


__all__ = ["LLMProvider", "load_providers"]
