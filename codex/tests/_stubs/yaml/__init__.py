from __future__ import annotations

import json
from typing import Any, List, Tuple


def _strip_comments(text: str) -> List[Tuple[int, str]]:
    lines: List[Tuple[int, str]] = []
    for raw_line in text.splitlines():
        if "#" in raw_line:
            raw_line = raw_line.split("#", 1)[0]
        if not raw_line.strip():
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        lines.append((indent, raw_line.strip()))
    return lines


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return None
    if value[0] in '"\'' and value[-1] == value[0]:
        return value[1:-1]
    lower = value.lower()
    if lower in {"true", "false"}:
        return lower == "true"
    if lower in {"null", "none"}:
        return None
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        pass
    if value.startswith("[") or value.startswith("{"):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _parse_block(lines: List[Tuple[int, str]], start: int, indent: int) -> Tuple[Any, int]:
    seq_mode = False
    mapping: dict[str, Any] = {}
    sequence: list[Any] = []
    index = start
    while index < len(lines):
        current_indent, content = lines[index]
        if current_indent < indent:
            break
        if content.startswith("- "):
            seq_mode = True
            item_content = content[2:].strip()
            index += 1
            if item_content:
                if item_content.endswith(":"):
                    key = item_content[:-1].strip()
                    value, index = _parse_block(lines, index, current_indent + 2)
                    sequence.append({key: value})
                else:
                    sequence.append(_parse_scalar(item_content))
            else:
                value, index = _parse_block(lines, index, current_indent + 2)
                sequence.append(value)
            continue

        key, sep, remainder = content.partition(":")
        key = key.strip()
        if not sep:
            raise ValueError(f"Invalid YAML line: {content}")
        remainder = remainder.strip()
        index += 1
        if remainder:
            value = _parse_scalar(remainder)
        else:
            value, index = _parse_block(lines, index, current_indent + 2)
        mapping[key] = value

    if seq_mode:
        # If we parsed any sequence entries, return the list.
        if mapping:
            sequence.append(mapping)  # pragma: no cover - defensive fallback
        return sequence, index
    return mapping, index


def safe_load(text: str) -> Any:
    stripped = text.lstrip()
    if not stripped:
        return {}
    if stripped[0] in "{[":
        return json.loads(stripped)

    lines = _strip_comments(text)
    if not lines:
        return {}
    value, _ = _parse_block(lines, 0, lines[0][0])
    return value
