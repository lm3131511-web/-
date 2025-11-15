from __future__ import annotations

import asyncio
import inspect
from typing import Any

from . import FastAPI, Request
from .responses import Response as FastAPIResponse


class Response:
    def __init__(self, status_code: int, data: Any) -> None:
        self.status_code = status_code
        self._data = data

    def json(self) -> Any:
        return self._data


class TestClient:
    __test__ = False

    def __init__(self, app: FastAPI) -> None:
        self.app = app

    def __enter__(self) -> "TestClient":
        for handler in getattr(self.app, "_startup_handlers", []):
            result = handler()
            if asyncio.iscoroutine(result):
                asyncio.run(result)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - context manager cleanup
        return None

    def get(self, path: str) -> Response:
        return self._invoke("GET", path, {})

    def post(self, path: str, json: dict[str, Any] | None = None) -> Response:
        return self._invoke("POST", path, json or {})

    def _invoke(self, method: str, path: str, payload: dict[str, Any]) -> Response:
        route = self.app.routes.get((method, path))
        if not route:
            return Response(404, None)
        endpoint = route["endpoint"]
        dependencies = route["dependencies"]
        request = Request(self.app)
        kwargs: dict[str, Any] = {}
        for name, dep in dependencies:
            value = dep(request)
            if asyncio.iscoroutine(value):
                value = asyncio.run(value)
            kwargs[name] = value
        signature = inspect.signature(endpoint)
        for name, param in signature.parameters.items():
            if name in kwargs:
                continue
            if param.annotation is Request or name == "request":
                kwargs[name] = request
            elif name in payload:
                kwargs[name] = payload[name]
        result = endpoint(**kwargs)
        if asyncio.iscoroutine(result):
            result = asyncio.run(result)
        if isinstance(result, FastAPIResponse):
            status_code = result.status_code
            data = result.json()
        else:
            status_code = 200 if not isinstance(result, Response) else result.status_code
            data = result if not isinstance(result, Response) else result.json()
        return Response(status_code, data)
