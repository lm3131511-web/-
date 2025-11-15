from __future__ import annotations

from typing import Any, Dict

from .base import HTTPPromptProvider
from .errors import ProviderResponseError


class ClaudeSonnetProvider(HTTPPromptProvider):
    name = "claude"
    endpoint_path = "/v1/messages"

    def __init__(self, settings, system_prompt: str, client_factory=None) -> None:
        super().__init__(settings, system_prompt, self.name, client_factory)

    async def complete(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        headers = {
            "x-api-key": self._api_key(),
            "anthropic-version": self.config.api_version or "2023-06-01",
            "content-type": "application/json",
        }
        body: Dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": self.config.max_output_tokens or 1024,
            "temperature": 0,
            "system": self.system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": self._format_payload(payload),
                        }
                    ],
                }
            ],
        }
        data = await self._post_json(headers, body)
        try:
            content_blocks = data["content"]
        except KeyError as exc:
            raise ProviderResponseError("Claude response missing content") from exc
        text_fragments = [
            block.get("text", "")
            for block in content_blocks
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        if not text_fragments:
            raise ProviderResponseError("Claude response missing text block")
        content = "".join(text_fragments)
        return self._parse_content(content)
