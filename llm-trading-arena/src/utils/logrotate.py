from __future__ import annotations

import shutil
from pathlib import Path

from .time import now_utc_iso


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def rotate_if_big(path: Path, *, max_bytes: int = 5_000_000) -> None:
    if not path.exists() or path.stat().st_size < max_bytes:
        return
    archive_dir = path.parent / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    timestamp = now_utc_iso().replace(":", "-")
    target = archive_dir / f"{path.name}.{timestamp}"
    shutil.move(str(path), target)


def rotate_daily(path: Path) -> None:
    if not path.exists():
        return
    day_marker = now_utc_iso().split("T")[0]
    archive_dir = path.parent / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    target = archive_dir / f"{path.name}.{day_marker}"
    if not target.exists():
        shutil.copy2(path, target)
