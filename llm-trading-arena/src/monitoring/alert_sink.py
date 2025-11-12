from __future__ import annotations

from typing import Protocol


class AlertSink(Protocol):
    async def publish(self, message: str, level: str) -> None:  # pragma: no cover
        ...
