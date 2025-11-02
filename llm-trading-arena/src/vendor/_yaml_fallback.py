from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List


class YAMLError(Exception):
    pass


@dataclass
class _Frame:
    container: Any
    indent: int
    last_key: str | None = None


def _parse_scalar(value: str) -> Any:
    if value.startswith("{") and value.endswith("}"):
        inner = value[1:-1].strip()
        if not inner:
            return {}
        result: Dict[str, Any] = {}
        for part in inner.split(","):
            key, _, val = part.partition(":")
            result[key.strip().strip('"').strip("'")] = _parse_scalar(val.strip())
        return result
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part.strip()) for part in inner.split(",")]
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none"}:
        return None
    try:
        if any(ch in value for ch in (".", "e", "E")):
            return float(value)
        return int(value)
    except ValueError:
        pass
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def safe_load(text: str) -> Dict[str, Any]:
    root: Dict[str, Any] = {}
    stack: List[_Frame] = [_Frame(root, -1, None)]
    for raw_line in text.splitlines():
        stripped_comment = raw_line.split("#", 1)[0]
        if not stripped_comment.strip():
            continue
        indent = len(stripped_comment) - len(stripped_comment.lstrip(" "))
        content = stripped_comment.strip()
        while stack and indent <= stack[-1].indent:
            stack.pop()
        if not stack:
            raise YAMLError(f"invalid indentation at line: {raw_line}")
        frame = stack[-1]
        container = frame.container
        if content.startswith("- "):
            value_part = content[2:].strip()
            if not isinstance(container, list):
                if isinstance(container, dict):
                    if frame.last_key is None:
                        raise YAMLError("list item without key context")
                    new_list: List[Any] = []
                    container[frame.last_key] = new_list
                    frame.container = new_list
                    container = new_list
                else:
                    raise YAMLError("list item in non-container")
            if not value_part:
                new_dict: Dict[str, Any] = {}
                container.append(new_dict)
                stack.append(_Frame(new_dict, indent, None))
            elif ":" in value_part:
                key, _, rest = value_part.partition(":")
                item: Dict[str, Any] = {key.strip(): _parse_scalar(rest.strip())}
                container.append(item)
            else:
                container.append(_parse_scalar(value_part))
            continue
        key, sep, value_part = content.partition(":")
        if not sep:
            raise YAMLError(f"invalid line: {raw_line}")
        key = key.strip()
        value_part = value_part.strip()
        if isinstance(container, list):
            new_dict: Dict[str, Any] = {}
            container.append(new_dict)
            container = new_dict
            stack.append(_Frame(container, indent, key))
        if value_part == "":
            new_container: Dict[str, Any] = {}
            container[key] = new_container
            stack.append(_Frame(new_container, indent, key))
        else:
            container[key] = _parse_scalar(value_part)
            frame.last_key = key
    return root


__all__ = ["safe_load", "YAMLError"]
