"""Vendor re-export helpers for third-party libraries."""

try:  # pragma: no cover
    import httpx  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    from . import _httpx_fallback as httpx  # type: ignore

try:  # pragma: no cover
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    from . import _yaml_fallback as yaml  # type: ignore

__all__ = ["httpx", "yaml"]
