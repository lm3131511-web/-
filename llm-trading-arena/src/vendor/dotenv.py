"""Re-export python-dotenv helpers with an offline fallback."""

try:  # pragma: no cover - executed when dependency is available
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    from ._dotenv_fallback import load_dotenv  # type: ignore

__all__ = ["load_dotenv"]
