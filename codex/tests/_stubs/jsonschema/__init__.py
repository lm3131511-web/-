from __future__ import annotations

from typing import Any, Dict, List


class ValidationError(Exception):
    pass


def validate(instance: Dict[str, Any], schema: Dict[str, Any]) -> None:
    if schema.get("type") != "object":
        raise ValidationError("Only object schemas are supported")
    if not isinstance(instance, dict):
        raise ValidationError("Instance must be a dict")
    required = schema.get("required", [])
    for field in required:
        if field not in instance:
            raise ValidationError(f"Missing field {field}")
    properties = schema.get("properties", {})
    for key, value in instance.items():
        prop_schema = properties.get(key)
        if not prop_schema:
            continue
        expected_type = prop_schema.get("type")
        if expected_type == "string" and not isinstance(value, str):
            raise ValidationError(f"Field {key} must be a string")
        if expected_type == "number" and not isinstance(value, (int, float)):
            raise ValidationError(f"Field {key} must be a number")
        if expected_type == "integer" and not isinstance(value, int):
            raise ValidationError(f"Field {key} must be an integer")
        if expected_type == "boolean" and not isinstance(value, bool):
            raise ValidationError(f"Field {key} must be boolean")
        if expected_type == "array" and not isinstance(value, list):
            raise ValidationError(f"Field {key} must be an array")
        if "maxLength" in prop_schema and isinstance(value, str) and len(value) > prop_schema["maxLength"]:
            raise ValidationError(f"Field {key} exceeds maxLength")
        if "enum" in prop_schema and value not in prop_schema["enum"]:
            raise ValidationError(f"Field {key} must be one of {prop_schema['enum']}")
    additional = schema.get("additionalProperties", True)
    if not additional:
        allowed = set(properties.keys())
        for key in instance.keys():
            if key not in allowed:
                raise ValidationError(f"Unknown field {key}")
