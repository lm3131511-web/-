from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Callable, Dict, Iterable, List, Tuple


class HTTPException(Exception):
    """Minimal stand-in for :class:`fastapi.HTTPException`."""

    def __init__(self, status_code: int, detail: str | None = None) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class Request:
    """Very small request object used by the tests."""

    def __init__(self, app: Any | None = None) -> None:
        self.app = app or SimpleNamespace(state=SimpleNamespace())

    @property
    def state(self) -> Any:
        return getattr(self.app, "state", SimpleNamespace())


class _Status:
    HTTP_200_OK = 200
    HTTP_401_UNAUTHORIZED = 401
    HTTP_403_FORBIDDEN = 403
    HTTP_404_NOT_FOUND = 404
    HTTP_500_INTERNAL_SERVER_ERROR = 500


status = _Status()


def Depends(dependency: Callable[..., Any]) -> Callable[..., Any]:  # pragma: no cover - identity for tests
    return dependency


class APIRouter:
    """Subset of the router API required by the tests."""

    def __init__(self) -> None:
        self.routes: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def add_api_route(
        self,
        path: str,
        endpoint: Callable[..., Any],
        methods: Iterable[str],
        dependencies: List[Tuple[str, Callable[..., Any]]] | None = None,
    ) -> Callable[..., Any]:
        for method in methods:
            self.routes[(method.upper(), path)] = {
                "endpoint": endpoint,
                "dependencies": dependencies or [],
            }
        return endpoint

    def get(
        self,
        path: str,
        *,
        dependencies: List[Tuple[str, Callable[..., Any]]] | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return self.add_api_route(path, func, ["GET"], dependencies)

        return decorator

    def post(
        self,
        path: str,
        *,
        dependencies: List[Tuple[str, Callable[..., Any]]] | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return self.add_api_route(path, func, ["POST"], dependencies)

        return decorator


class FastAPI(APIRouter):
    """Narrow implementation of :class:`fastapi.FastAPI` used in tests."""

    def __init__(self, *_, **__) -> None:
        super().__init__()
        self.state = SimpleNamespace()
        self._startup_handlers: List[Callable[[], Any]] = []

    def include_router(self, router: APIRouter, *, prefix: str = "") -> None:
        for (method, path), route in router.routes.items():
            full_path = f"{prefix}{path}" if prefix else path
            self.routes[(method, full_path)] = route

    def on_event(self, _event: str) -> Callable[[Callable[[], Any]], Callable[[], Any]]:
        def decorator(func: Callable[[], Any]) -> Callable[[], Any]:
            self._startup_handlers.append(func)
            return func

        return decorator

    async def __call__(self, request: Request) -> Any:  # pragma: no cover - ASGI stub
        raise NotImplementedError("The stub FastAPI application is not ASGI callable")


__all__ = [
    "APIRouter",
    "Depends",
    "FastAPI",
    "HTTPException",
    "Request",
    "status",
]
