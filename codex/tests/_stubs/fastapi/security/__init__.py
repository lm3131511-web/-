from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .. import Request


@dataclass
class HTTPAuthorizationCredentials:
    scheme: str = "Bearer"
    credentials: Optional[str] = None


class HTTPBearer:
    def __init__(self, auto_error: bool = True) -> None:
        self.auto_error = auto_error

    def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:  # pragma: no cover - simple stub
        return None


__all__ = ["HTTPAuthorizationCredentials", "HTTPBearer"]
