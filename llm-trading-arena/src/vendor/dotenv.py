"""Thin re-export of python-dotenv helpers."""

try:  # pragma: no cover
    from dotenv import load_dotenv  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    from ._dotenv_fallback import load_dotenv  # type: ignore

__all__ = ["load_dotenv"]
