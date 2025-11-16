from __future__ import annotations

from typing import Any

from ...config.models import ProviderConfig
from ...monitoring.metrics import trusted_source_counter
from ..sanitize import filter_trusted
from .base import BaseNewsProvider


class TwitterProvider(BaseNewsProvider):
    def __init__(self, config: ProviderConfig, fetcher=None) -> None:  # type: ignore[override]
        super().__init__(name="twitter", config=config, fetcher=fetcher)

    async def fetch(self) -> list[dict[str, Any]]:
        items = await super().fetch()
        whitelist = {handle.lower() for handle in self.config.trusted_sources or []}
        min_followers = self.config.min_followers or 0
        if whitelist:
            trusted_items = filter_trusted(items, whitelist=whitelist, min_followers=min_followers)
        else:
            trusted_items = items
        if trusted_items:
            trusted_source_counter.labels(provider=self.name).inc(len(trusted_items))
        for item in trusted_items:
            item.setdefault("source", {})
            item["source"].setdefault("handle", item["source"].get("handle", ""))
            item["provider"] = self.name
            item["trusted"] = True
        return trusted_items
