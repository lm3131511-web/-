from __future__ import annotations

import shutil
import time
from pathlib import Path

from .time import now_utc_iso


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def rotate_if_big(
    path: Path,
    *,
    max_bytes: int = 5_000_000,
    max_files: int = 30,
    max_retention_days: int = 30,
) -> None:
    if not path.exists() or path.stat().st_size < max_bytes:
        return
    archive_dir = path.parent / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    timestamp = now_utc_iso().replace(":", "-")
    target = archive_dir / f"{path.name}.{timestamp}"
    shutil.move(str(path), target)
    _prune_archive(archive_dir, path.name, max_files=max_files, max_retention_days=max_retention_days)


def rotate_daily(path: Path) -> None:
    if not path.exists():
        return
    day_marker = now_utc_iso().split("T")[0]
    archive_dir = path.parent / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    target = archive_dir / f"{path.name}.{day_marker}"
    if not target.exists():
        shutil.copy2(path, target)


def _prune_archive(archive_dir: Path, base_name: str, *, max_files: int, max_retention_days: int) -> None:
    files = sorted(archive_dir.glob(f"{base_name}.*"), key=lambda item: item.stat().st_mtime, reverse=True)
    for extra in files[max_files:]:
        extra.unlink(missing_ok=True)
    if max_retention_days <= 0:
        return
    cutoff_ts = time.time() - (max_retention_days * 86400)
    for file in files:
        if file.stat().st_mtime < cutoff_ts:
            file.unlink(missing_ok=True)
