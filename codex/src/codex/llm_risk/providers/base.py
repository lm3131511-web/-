from __future__ import annotations

import asyncio
import json
import os
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict

import httpx

from ...config.models import LLMProviderConfig, Settings
from .errors import ProviderError, ProviderResponseError, ProviderTransportError


ClientFactory = Callable[[], httpx.AsyncClient]


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


class HTTPPromptProvider(LLMProvider):
    endpoint_path: str

    def __init__(
        self,
        settings: Settings,
        system_prompt: str,
        provider_name: str,
        client_factory: ClientFactory | None = None,
    ) -> None:
        self.settings = settings
        self.system_prompt = system_prompt
        self.name = provider_name
        self.config: LLMProviderConfig = settings.get_llm_provider(provider_name)
        self._timeout = settings.llm.timeout_ms / 1000
        self._attempts = settings.llm.retry.max + 1
        self._backoff = settings.llm.retry.backoff_ms / 1000
        self.base_url = self.config.base_url.rstrip("/")
        self._client_factory = client_factory or self._default_client_factory

    async def _post_json(self, headers: Dict[str, str], body: Dict[str, Any]) -> Dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self._attempts):
            try:
                async with self._client_factory() as client:
                    response = await client.post(
                        self.base_url + self.endpoint_path,
                        headers=headers,
                        json=body,
                    )
            except httpx.TimeoutException as exc:  # pragma: no cover - network failure
                last_error = exc
            except httpx.HTTPError as exc:
                last_error = exc
            else:
                if response.status_code >= 400:
                    last_error = ProviderResponseError(
                        f"HTTP {response.status_code} from {self.name}"
                    )
                else:
                    try:
                        return response.json()
                    except json.JSONDecodeError as exc:
                        last_error = exc
            if attempt < self._attempts - 1:
                await asyncio.sleep(self._backoff)
        if isinstance(last_error, ProviderResponseError):
            raise last_error
        if last_error:
            raise ProviderTransportError(str(last_error)) from last_error
        raise ProviderTransportError(f"{self.name} request failed")

    def _default_client_factory(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self._timeout)

    def _api_key(self) -> str:
        value = os.getenv(self.config.api_key_env)
        if not value:
            raise ProviderTransportError(f"Missing API key for {self.name}")
        return value

    @staticmethod
    def _format_payload(payload: Dict[str, Any]) -> str:
        allowed = {
            "features": payload.get("features", {}),
            "sentiment": payload.get("sentiment", {}),
            "meta": payload.get("meta", {}),
            "prompt_version": payload.get("prompt_version"),
            "stale_correlation": payload.get("stale_correlation", False),
        }
        return json.dumps(allowed, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def _parse_content(content: str) -> Dict[str, Any]:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ProviderResponseError("Provider returned non-JSON content") from exc
        if not isinstance(parsed, dict):
            raise ProviderResponseError("Provider response must be a JSON object")
        return parsed
