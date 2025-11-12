"""Thin re-export of Pydantic primitives for centralised imports."""

try:  # pragma: no cover
    from pydantic import BaseModel, Field  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    from ._pydantic_fallback import BaseModel, Field  # type: ignore

__all__ = ["BaseModel", "Field"]
