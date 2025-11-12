from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import (
    Any,
    Dict,
    Iterable,
    ClassVar,
    List,
    Mapping,
    MutableMapping,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
    Literal,
)

ConfigDict = Dict[str, Any]


class ValidationError(Exception):
    """Lightweight validation error compatible with the parts of Pydantic v2 we rely on."""

    def __init__(self, errors: Iterable[Dict[str, Any]]) -> None:
        self.errors = list(errors)
        message = "; ".join(f"{err.get('loc')}: {err.get('msg')}" for err in self.errors) or "validation error"
        super().__init__(message)


@dataclass
class FieldInfo:
    default: Any = None
    default_factory: Any | None = None
    metadata: Dict[str, Any] | None = None


_MISSING = object()
T = TypeVar("T", bound="BaseModel")


def Field(*, default: Any = _MISSING, default_factory: Any | None = None, **metadata: Any) -> FieldInfo:
    if default is _MISSING:
        default = None
    return FieldInfo(default=default, default_factory=default_factory, metadata=metadata or None)


def _is_field_info(value: Any) -> bool:
    return isinstance(value, FieldInfo)


def _extract_default(cls: Type["BaseModel"], name: str) -> Tuple[bool, Any]:
    attr = getattr(cls, name, _MISSING)
    if _is_field_info(attr):
        if attr.default_factory is not None:
            return True, attr.default_factory()
        if attr.default is not _MISSING:
            return True, copy.deepcopy(attr.default)
        return False, None
    if attr is not _MISSING:
        return True, copy.deepcopy(attr)
    return False, None


def _annotation_is_optional(annotation: Any) -> bool:
    origin = get_origin(annotation)
    if origin is Union:
        return type(None) in get_args(annotation)
    return False


def _coerce_literal(annotation: Any, value: Any) -> Any:
    allowed = get_args(annotation)
    if value in allowed:
        return value
    raise TypeError(f"value {value!r} not in literal choices {allowed}")


_SIMPLE_TYPE_CASTERS: Dict[Any, Any] = {
    str: str,
    int: int,
    float: float,
    bool: bool,
}


def _coerce_value(annotation: Any, value: Any) -> Any:
    if annotation is Any or annotation is None:
        return value
    origin = get_origin(annotation)
    if origin is None:
        if isinstance(annotation, type):
            if issubclass(annotation, BaseModel):
                if isinstance(value, annotation):
                    return value
                if isinstance(value, Mapping):
                    return annotation(**dict(value))
                if value is None and _annotation_is_optional(annotation):
                    return None
                raise TypeError(f"value for {annotation.__name__} must be mapping")
            caster = _SIMPLE_TYPE_CASTERS.get(annotation)
            if caster is not None:
                if value is None and _annotation_is_optional(annotation):
                    return None
                return caster(value)
        return value
    if origin in (list, List):
        item_type = get_args(annotation)[0] if get_args(annotation) else Any
        if value is None:
            return []
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
            raise TypeError("expected sequence")
        return [_coerce_value(item_type, item) for item in value]
    if origin in (dict, Dict):
        args = get_args(annotation)
        key_type = args[0] if args else Any
        value_type = args[1] if len(args) > 1 else Any
        if value is None:
            return {}
        if not isinstance(value, MutableMapping):
            raise TypeError("expected mapping")
        return {
            _coerce_value(key_type, key): _coerce_value(value_type, val)
            for key, val in value.items()
        }
    if origin in (tuple, Tuple):
        args = get_args(annotation)
        if not isinstance(value, Sequence):
            raise TypeError("expected tuple")
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(_coerce_value(args[0], item) for item in value)
        if len(args) != len(value):
            raise TypeError("tuple length mismatch")
        return tuple(_coerce_value(arg, item) for arg, item in zip(args, value))
    if origin is Union:
        args = get_args(annotation)
        if value is None and any(arg is type(None) for arg in args):
            return None
        last_exc: Exception | None = None
        for option in args:
            if option is type(None):
                continue
            try:
                return _coerce_value(option, value)
            except Exception as exc:  # pragma: no cover
                last_exc = exc
        if last_exc is not None:
            raise last_exc
        return value
    if origin is Literal:
        return _coerce_literal(annotation, value)
    return value


def _dump_value(value: Any, *, mode: str | None = None) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode=mode)
    if isinstance(value, list):
        return [_dump_value(item, mode=mode) for item in value]
    if isinstance(value, tuple):
        return [_dump_value(item, mode=mode) for item in value]
    if isinstance(value, dict):
        return {key: _dump_value(val, mode=mode) for key, val in value.items()}
    return value


def _annotation_to_json_type(annotation: Any) -> Dict[str, Any]:
    origin = get_origin(annotation)
    if origin is Literal:
        return {"enum": list(get_args(annotation))}
    if origin in (list, List):
        item_annotation = get_args(annotation)[0] if get_args(annotation) else Any
        return {"type": "array", "items": _annotation_to_json_type(item_annotation)}
    if origin in (dict, Dict):
        return {"type": "object"}
    if origin in (tuple, Tuple):
        return {"type": "array"}
    if origin is Union:
        args = [arg for arg in get_args(annotation) if arg is not type(None)]
        if len(args) == 1:
            schema = _annotation_to_json_type(args[0])
            return {**schema, "nullable": True}
        return {"anyOf": [_annotation_to_json_type(arg) for arg in args]}
    if isinstance(annotation, type):
        if issubclass(annotation, BaseModel):
            return {"$ref": f"#/definitions/{annotation.__name__}"}
        mapping = {str: "string", int: "integer", float: "number", bool: "boolean"}
        json_type = mapping.get(annotation)
        if json_type:
            return {"type": json_type}
    return {}


def _model_annotations(cls: Type["BaseModel"]) -> Dict[str, Any]:
    try:
        annotations = get_type_hints(cls, include_extras=True)
    except Exception:  # pragma: no cover - fallback for unsupported hints
        annotations = cls.__dict__.get("__annotations__", {})
    cleaned: Dict[str, Any] = {}
    for name, annotation in annotations.items():
        if get_origin(annotation) is ClassVar:
            continue
        cleaned[name] = annotation
    return cleaned


class BaseModel:
    model_config: ClassVar[ConfigDict] = {"extra": "ignore"}

    def __init__(self, **data: Any) -> None:
        annotations = _model_annotations(self.__class__)
        values: Dict[str, Any] = {}
        extras: Dict[str, Any] = dict(data)
        errors: List[Dict[str, Any]] = []
        for name, annotation in annotations.items():
            raw_value = extras.pop(name, _MISSING)
            if raw_value is _MISSING:
                has_default, default_value = _extract_default(self.__class__, name)
                if has_default:
                    raw_value = default_value
                else:
                    raw_value = None
            try:
                values[name] = _coerce_value(annotation, raw_value)
            except Exception as exc:
                errors.append({"loc": [name], "msg": str(exc)})
        extra_mode = self.model_config.get("extra", "ignore")
        if errors:
            raise ValidationError(errors)
        if extras and extra_mode == "forbid":
            raise ValidationError([{"loc": [key], "msg": "unexpected field"} for key in extras])
        self.__dict__.update(values)
        if extra_mode == "allow":
            self.model_extra = extras
        elif extra_mode == "ignore":
            self.model_extra = {}
        else:
            self.model_extra = {}

    def model_dump(self, *, mode: str | None = None) -> Dict[str, Any]:
        annotations = _model_annotations(self.__class__)
        result: Dict[str, Any] = {}
        for name in annotations:
            result[name] = _dump_value(getattr(self, name), mode=mode)
        if self.model_extra:
            if mode == "json":
                result.update({k: _dump_value(v, mode=mode) for k, v in self.model_extra.items()})
            else:
                result.update(self.model_extra)
        return result

    def model_dump_json(self, *, mode: str | None = None) -> str:
        return json.dumps(self.model_dump(mode=mode or "json"))

    def model_copy(self: T, *, update: Dict[str, Any] | None = None) -> T:
        data = self.model_dump()
        if update:
            data.update(update)
        return self.__class__(**data)

    @classmethod
    def model_validate(cls: Type[T], data: Dict[str, Any]) -> T:
        if not isinstance(data, dict):
            raise ValidationError([{"loc": ["__root__"], "msg": "data must be a dict"}])
        return cls(**data)

    @classmethod
    def model_json_schema(cls) -> Dict[str, Any]:
        annotations = _model_annotations(cls)
        properties: Dict[str, Any] = {}
        required: List[str] = []
        for name, annotation in annotations.items():
            properties[name] = _annotation_to_json_type(annotation) or {"title": name}
            has_default, _ = _extract_default(cls, name)
            if not has_default:
                required.append(name)
        schema: Dict[str, Any] = {
            "title": cls.__name__,
            "type": "object",
            "properties": properties,
        }
        if required:
            schema["required"] = required
        schema_meta = getattr(cls, "schema_meta", None)
        if isinstance(schema_meta, dict):
            schema["schema_meta"] = schema_meta
        return schema


def root_validator(*args: Any, **kwargs: Any):  # pragma: no cover - passthrough decorator
    def decorator(func):
        return func

    return decorator


def validator(*args: Any, **kwargs: Any):  # pragma: no cover - passthrough decorator
    def decorator(func):
        return func

    return decorator


__all__ = [
    "BaseModel",
    "Field",
    "ValidationError",
    "ConfigDict",
    "root_validator",
    "validator",
]
