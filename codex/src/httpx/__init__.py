from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Callable, Optional
from urllib.parse import urlparse


class HTTPError(Exception):
    """Base HTTP client error."""


class TimeoutException(HTTPError):
    """Raised when the request times out."""


@dataclass
class URL:
    raw: str

    def __post_init__(self) -> None:
        parsed = urlparse(self.raw)
        self.scheme = parsed.scheme
        self.host = parsed.netloc
        self.path = parsed.path or "/"


class Request:
    def __init__(self, method: str, url: str, headers: Optional[dict[str, str]] = None, json_body: Any = None) -> None:
        self.method = method
        self.url = URL(url)
        self.headers = headers or {}
        self._json_body = json_body
        self.content = json.dumps(json_body) if json_body is not None else ""


class Response:
    def __init__(self, status_code: int, json: Any | None = None) -> None:
        self.status_code = status_code
        self._json = json

    def json(self) -> Any:
        if self._json is None:
            raise ValueError("No JSON payload")
        return self._json


class MockTransport:
    def __init__(self, handler: Callable[[Request], Response]) -> None:
        self.handler = handler


class AsyncClient:
    def __init__(self, *, timeout: float | None = None, transport: MockTransport | None = None) -> None:
        self.timeout = timeout
        self.transport = transport

    async def __aenter__(self) -> "AsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def post(self, url: str, *, headers: Optional[dict[str, str]] = None, json: Any = None) -> Response:
        if not self.transport:
            raise HTTPError("Network transport not available in stub httpx client")
        request = Request("POST", url, headers=headers, json_body=json)
        response = self.transport.handler(request)
        if asyncio.iscoroutine(response):
            response = await response
        if not isinstance(response, Response):
            raise HTTPError("MockTransport must return an httpx.Response")
        return response


__all__ = [
    "AsyncClient",
    "HTTPError",
    "MockTransport",
    "Request",
    "Response",
    "TimeoutException",
]
