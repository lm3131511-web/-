from __future__ import annotations

from typing import Any, Dict

from .base import HTTPPromptProvider
from .errors import ProviderResponseError


class QwenProvider(HTTPPromptProvider):
    name = "qwen"
    endpoint_path = "/chat/completions"

    def __init__(self, settings, system_prompt: str, client_factory=None) -> None:
        super().__init__(settings, system_prompt, self.name, client_factory)

    async def complete(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self._api_key()}",
            "Content-Type": "application/json",
        }
        body: Dict[str, Any] = {
            "model": self.config.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": self._format_payload(payload)},
            ],
        }
        if self.config.compatible_mode:
            body["response_format"] = {"type": "json_object"}
        data = await self._post_json(headers, body)
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderResponseError("Qwen response missing message content") from exc
        return self._parse_content(content)
