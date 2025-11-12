from __future__ import annotations

from typing import Any

from ...config.models import ProviderConfig
from .base import BaseNewsProvider


class RedditProvider(BaseNewsProvider):
    def __init__(self, config: ProviderConfig, fetcher=None) -> None:  # type: ignore[override]
        super().__init__(name="reddit", config=config, fetcher=fetcher)

    async def fetch(self) -> list[dict[str, Any]]:
        items = await super().fetch()
        for item in items:
            item["provider"] = self.name
        return items
