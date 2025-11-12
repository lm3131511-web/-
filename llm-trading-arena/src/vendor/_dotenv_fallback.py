from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

__all__ = ["load_dotenv"]


def _iter_pairs(lines: Iterable[str]) -> Iterable[tuple[str, str]]:
    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        yield key.strip(), value.strip().strip('"').strip("'")


def load_dotenv(path: str | None = None) -> None:
    target = Path(path or ".env")
    if not target.exists():
        return
    with target.open("r", encoding="utf-8") as handle:
        for key, value in _iter_pairs(handle):
            os.environ.setdefault(key, value)
