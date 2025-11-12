from __future__ import annotations

import inspect
from datetime import datetime
from typing import Any, Awaitable, Callable, Iterable, Sequence

from ...config.models import ProviderConfig
from ...utils.time import utc_now

FetchCallable = Callable[[ProviderConfig], Awaitable[Sequence[dict[str, Any]]] | Sequence[dict[str, Any]]]


class BaseNewsProvider:
    """Utility base class for provider implementations."""

    def __init__(self, name: str, config: ProviderConfig, fetcher: FetchCallable | None = None) -> None:
        self.name = name
        self.config = config
        self._fetcher = fetcher or (lambda _config: [])

    async def fetch(self) -> list[dict[str, Any]]:
        payloads = await self._invoke_fetcher()
        payloads = self._filter_window(payloads, self.config.window_min)
        return list(payloads)[: self.config.max_items]

    async def _invoke_fetcher(self) -> Sequence[dict[str, Any]]:
        result = self._fetcher(self.config)
        if inspect.isawaitable(result):
            result = await result  # type: ignore[assignment]
        return list(result or [])

    @staticmethod
    def _filter_window(payloads: Iterable[dict[str, Any]], window_min: int) -> list[dict[str, Any]]:
        if window_min <= 0:
            return list(payloads)
        cutoff = utc_now().timestamp() - window_min * 60
        filtered: list[dict[str, Any]] = []
        for item in payloads:
            ts = BaseNewsProvider._coerce_timestamp(item.get("timestamp"))
            if ts is None or ts >= cutoff:
                filtered.append(item)
        return filtered

    @staticmethod
    def _coerce_timestamp(value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, datetime):
            return value.timestamp()
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
            except ValueError:
                return None
        return None
