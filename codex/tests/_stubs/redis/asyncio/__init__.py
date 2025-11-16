from __future__ import annotations


class _DummyRedis:
    async def __aenter__(self) -> "_DummyRedis":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def ping(self) -> bool:
        return True


def from_url(url: str) -> _DummyRedis:  # pragma: no cover - simple stub
    return _DummyRedis()


__all__ = ["from_url"]
