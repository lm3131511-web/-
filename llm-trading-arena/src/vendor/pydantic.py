"""Re-export Pydantic primitives with an offline fallback."""

try:  # pragma: no cover - executed when real dependency is available
    from pydantic import BaseModel, Field, ValidationError, root_validator, validator
except ImportError:  # pragma: no cover
    from ._pydantic_fallback import (  # type: ignore
        BaseModel,
        Field,
        ValidationError,
        root_validator,
        validator,
    )

__all__ = ["BaseModel", "Field", "ValidationError", "root_validator", "validator"]
