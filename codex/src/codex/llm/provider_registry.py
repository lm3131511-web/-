from __future__ import annotations

from typing import Dict, Iterable, List

from ..config.models import Settings
from ..llm_risk.providers.base import LLMProvider
from ..llm_risk.providers.claude_sonnet import ClaudeSonnetProvider
from ..llm_risk.providers.deepseek import DeepSeekProvider
from ..llm_risk.providers.qwen import QwenProvider


class ProviderRegistry:
    def __init__(self, providers: Iterable[LLMProvider]):
        self._providers: Dict[str, LLMProvider] = {provider.name: provider for provider in providers}

    def get(self, name: str) -> LLMProvider:
        if name not in self._providers:
            raise KeyError(f"Provider {name} is not registered")
        return self._providers[name]

    def values(self) -> List[LLMProvider]:
        return list(self._providers.values())


def build_registry(settings: Settings, system_prompt: str) -> ProviderRegistry:
    providers: List[LLMProvider] = [
        QwenProvider(settings, system_prompt),
        DeepSeekProvider(settings, system_prompt),
        ClaudeSonnetProvider(settings, system_prompt),
    ]
    return ProviderRegistry(providers)


def provider_order(settings: Settings) -> List[str]:
    order: List[str] = []
    seen = set()
    primary = settings.llm.primary
    if primary not in settings.llm_providers:
        raise KeyError(f"Primary provider '{primary}' is not configured")
    for name in [primary, *settings.llm.fallback_chain]:
        if name and name not in seen:
            seen.add(name)
            order.append(name)
    return order
