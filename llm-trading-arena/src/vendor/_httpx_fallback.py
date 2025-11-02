from __future__ import annotations

import asyncio
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Mapping, MutableMapping, Optional


class HTTPError(Exception):
    pass


class ConnectError(HTTPError):
    pass


class HTTPStatusError(HTTPError):
    def __init__(self, status_code: int, message: str, *, response: "Response") -> None:
        super().__init__(f"HTTP {status_code}: {message}")
        self.response = response
        self.status_code = status_code


@dataclass
class Response:
    status_code: int
    headers: Mapping[str, str]
    content: bytes

    def json(self) -> Any:
        if not self.content:
            return None
        return json.loads(self.content.decode("utf-8"))

    def text(self, encoding: str = "utf-8") -> str:
        return self.content.decode(encoding)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise HTTPStatusError(self.status_code, self.text(), response=self)


class AsyncClient:
    def __init__(self, base_url: str | None = None, timeout: float | None = None, verify: bool = True) -> None:
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.timeout = timeout or 10.0
        self.verify = verify
        self._closed = False

    async def __aenter__(self) -> "AsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        self._closed = True

    async def get(self, url: str, *, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Response:
        return await self._request("GET", url, params=params, headers=headers)

    async def post(
        self,
        url: str,
        *,
        data: Optional[MutableMapping[str, Any]] = None,
        json: Any = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Response:
        return await self._request("POST", url, data=data, json=json, headers=headers)

    async def delete(
        self,
        url: str,
        *,
        data: Optional[MutableMapping[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Response:
        return await self._request("DELETE", url, data=data, headers=headers)

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[MutableMapping[str, Any]] = None,
        json: Any = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Response:
        if self._closed:
            raise HTTPError("client closed")
        full_url = self._merge_url(url)
        if params:
            query = urllib.parse.urlencode({k: _stringify(v) for k, v in params.items()})
            separator = "&" if urllib.parse.urlparse(full_url).query else "?"
            full_url = f"{full_url}{separator}{query}"
        body: bytes | None = None
        request_headers: Dict[str, str] = {"User-Agent": "httpx-lite"}
        if headers:
            request_headers.update(headers)
        if json is not None:
            body = json_dumps(json).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")
        elif data is not None:
            if isinstance(data, Mapping):
                body = urllib.parse.urlencode({k: _stringify(v) for k, v in data.items()}).encode("utf-8")
                request_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
            else:
                raise TypeError("data must be mapping")
        request = urllib.request.Request(full_url, data=body, method=method.upper(), headers=request_headers)
        ssl_context = ssl.create_default_context() if self.verify else ssl._create_unverified_context()
        loop = asyncio.get_running_loop()

        def _do_request() -> Response:
            try:
                with urllib.request.urlopen(request, timeout=self.timeout, context=ssl_context) as resp:
                    headers_map = {k: v for k, v in resp.getheaders()}
                    return Response(resp.status, headers_map, resp.read())
            except urllib.error.HTTPError as exc:
                headers_map = {k: v for k, v in exc.headers.items()} if exc.headers else {}
                return Response(exc.code, headers_map, exc.read() if exc.fp else b"")
            except urllib.error.URLError as exc:  # pragma: no cover - network issues
                raise ConnectError(str(exc)) from exc

        response = await loop.run_in_executor(None, _do_request)
        return response

    def _merge_url(self, url: str) -> str:
        if url.startswith("http://") or url.startswith("https://"):
            return url
        if not self.base_url:
            raise HTTPError("relative URL without base_url")
        return f"{self.base_url}/{url.lstrip('/')}"


def json_dumps(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"))


def _stringify(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return ",".join(_stringify(item) for item in value)
    return str(value)


__all__ = ["AsyncClient", "HTTPError", "HTTPStatusError", "Response", "ConnectError"]
