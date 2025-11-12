from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, get_args, get_origin, get_type_hints


@dataclass
class FieldInfo:
    default: Any = ...
    default_factory: Optional[Callable[[], Any]] = None
    ge: float | None = None
    le: float | None = None
    max_length: int | None = None


def Field(default: Any = ..., *, default_factory: Callable[[], Any] | None = None, ge: float | None = None, le: float | None = None, max_length: int | None = None) -> FieldInfo:
    return FieldInfo(default=default, default_factory=default_factory, ge=ge, le=le, max_length=max_length)


class ValidationError(ValueError):
    pass


class BaseModel:
    __annotations__: Dict[str, Any]
    model_config: Dict[str, Any] = {}

    def __init__(self, **data: Any) -> None:
        values: Dict[str, Any] = {}
        annotations = get_type_hints(type(self))
        for name, annotation in annotations.items():
            if name.startswith("__") or name == "model_config":
                continue
            info = getattr(type(self), name, None)
            if isinstance(info, FieldInfo):
                field_info = info
            else:
                field_info = FieldInfo(default=info)
            if name in data:
                value = data[name]
            elif field_info.default is not ...:
                value = field_info.default
            elif field_info.default_factory is not None:
                value = field_info.default_factory()
            else:
                raise ValidationError(f"Missing field {name}")
            value = self._coerce(annotation, value)
            if field_info.ge is not None and value is not None and value < field_info.ge:
                raise ValidationError(f"Field {name} must be >= {field_info.ge}")
            if field_info.le is not None and value is not None and value > field_info.le:
                raise ValidationError(f"Field {name} must be <= {field_info.le}")
            if field_info.max_length is not None and value is not None and len(value) > field_info.max_length:
                raise ValidationError(f"Field {name} length must be <= {field_info.max_length}")
            values[name] = value
        for key in data:
            if key not in values:
                values[key] = data[key]
        self.__dict__.update(values)

    def model_dump(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for key, value in self.__dict__.items():
            result[key] = self._dump_value(value)
        return result

    @classmethod
    def _dump_value(cls, value: Any) -> Any:
        if isinstance(value, BaseModel):
            return value.model_dump()
        if isinstance(value, list):
            return [cls._dump_value(item) for item in value]
        return value

    @classmethod
    def model_validate(cls, data: Any) -> "BaseModel":
        if isinstance(data, cls):
            return data
        if not isinstance(data, dict):
            raise ValidationError("Input must be a dict")
        return cls(**data)

    def model_copy(self, *, update: Dict[str, Any] | None = None) -> "BaseModel":
        data = self.model_dump()
        if update:
            data.update(update)
        return type(self)(**data)

    @classmethod
    def _coerce(cls, annotation: Any, value: Any) -> Any:
        origin = get_origin(annotation)
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            if isinstance(value, dict):
                return annotation(**value)
        if origin is list and isinstance(value, list):
            (inner,) = get_args(annotation) or (Any,)
            return [cls._coerce(inner, item) for item in value]
        if origin is dict and isinstance(value, dict):
            key_type, val_type = (get_args(annotation) + (Any, Any))[:2]
            return {key: cls._coerce(val_type, item) for key, item in value.items()}
        return value

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"{type(self).__name__}({self.model_dump()!r})"
