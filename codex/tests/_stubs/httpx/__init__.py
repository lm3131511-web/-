from __future__ import annotations

import asyncio
import inspect
import json as json_module
from dataclasses import dataclass
from typing import Any, Callable, Optional
from urllib.parse import urlparse

from fastapi import Request as FastAPIRequest
from fastapi.responses import Response as FastAPIResponse


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
        self.content = json_module.dumps(json_body) if json_body is not None else ""


class Response:
    def __init__(
        self,
        status_code: int,
        *,
        json: Any | None = None,
        text: str | None = None,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        self.status_code = status_code
        self._json = json
        if text is None:
            if json is None:
                self._text = ""
            else:
                self._text = json_module.dumps(json)
        else:
            self._text = text
        self.headers = headers or {}

    @property
    def text(self) -> str:
        return self._text

    def json(self) -> Any:
        if self._json is not None:
            return self._json
        if not self._text:
            raise ValueError("No JSON payload")
        return json_module.loads(self._text)


class MockTransport:
    def __init__(self, handler: Callable[[Request], Response]) -> None:
        self.handler = handler


class AsyncClient:
    def __init__(
        self,
        *,
        timeout: float | None = None,
        transport: MockTransport | None = None,
        app: Any | None = None,
        base_url: str | None = None,
    ) -> None:
        self.timeout = timeout
        self.transport = transport
        self.app = app
        self.base_url = base_url or ""
        self._startup_ran = False

    async def __aenter__(self) -> "AsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def get(self, url: str, *, headers: Optional[dict[str, str]] = None) -> Response:
        if self.app is not None:
            return await self._invoke_app("GET", url, headers=headers)
        return await self._dispatch_network("GET", url, headers=headers)

    async def post(
        self,
        url: str,
        *,
        headers: Optional[dict[str, str]] = None,
        json: Any = None,
    ) -> Response:
        if self.app is not None:
            return await self._invoke_app("POST", url, json_body=json, headers=headers)
        request = Request("POST", url, headers=headers, json_body=json)
        return await self._send_with_transport(request)

    async def _dispatch_network(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[dict[str, str]] = None,
    ) -> Response:
        if not self.transport:
            raise HTTPError("Network transport not available in stub httpx client")
        request = Request(method, url, headers=headers)
        return await self._send_with_transport(request)

    async def _send_with_transport(self, request: Request) -> Response:
        response = self.transport.handler(request)
        if asyncio.iscoroutine(response):
            response = await response
        if not isinstance(response, Response):
            raise HTTPError("MockTransport must return an httpx.Response")
        return response

    async def _invoke_app(
        self,
        method: str,
        url: str,
        *,
        json_body: Any = None,
        headers: Optional[dict[str, str]] = None,
    ) -> Response:
        await self._ensure_startup()
        path = self._extract_path(url)
        route = self.app.routes.get((method, path))
        if not route:
            return Response(404, text="")
        dependencies = route["dependencies"]
        fastapi_request = FastAPIRequest(self.app)
        kwargs: dict[str, Any] = {}
        for name, dependency in dependencies:
            value = dependency(fastapi_request)
            if inspect.isawaitable(value):
                value = await value
            kwargs[name] = value
        if isinstance(json_body, dict):
            kwargs.update(json_body)
        endpoint = route["endpoint"]
        signature = inspect.signature(endpoint)
        for name, param in signature.parameters.items():
            if name in kwargs:
                continue
            if param.annotation is FastAPIRequest or name == "request":
                kwargs[name] = fastapi_request
        result = endpoint(**kwargs)
        if inspect.isawaitable(result):
            result = await result
        return self._to_httpx_response(result)

    async def _ensure_startup(self) -> None:
        if self.app is None or self._startup_ran:
            return
        for handler in getattr(self.app, "_startup_handlers", []):
            outcome = handler()
            if inspect.isawaitable(outcome):
                await outcome
        self._startup_ran = True

    def _extract_path(self, url: str) -> str:
        if url.startswith("http"):
            parsed = urlparse(url)
            return parsed.path or "/"
        return url

    def _to_httpx_response(self, result: Any) -> Response:
        if isinstance(result, FastAPIResponse):
            text = getattr(result, "text", result.body.decode("utf-8"))
            json_payload: Any | None = None
            try:
                json_payload = result.json()
            except Exception:
                json_payload = None
            return Response(result.status_code, json=json_payload, text=text)
        if isinstance(result, dict):
            return Response(200, json=result)
        if isinstance(result, str):
            return Response(200, text=result)
        return Response(200, json=result)


__all__ = [
    "AsyncClient",
    "HTTPError",
    "MockTransport",
    "Request",
    "Response",
    "TimeoutException",
]
