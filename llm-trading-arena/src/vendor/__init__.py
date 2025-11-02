"""Vendor re-export helpers for third-party libraries.

The application prefers real third-party packages, but falls back to the
lightweight shims stored alongside the source tree when running in isolated
environments (e.g. CI without network access).
"""

try:  # pragma: no cover - exercised indirectly in integration tests
    import httpx  # type: ignore
except ImportError:  # pragma: no cover
    from . import _httpx_fallback as httpx  # type: ignore

try:  # pragma: no cover
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    from . import _yaml_fallback as yaml  # type: ignore

__all__ = ["httpx", "yaml"]
