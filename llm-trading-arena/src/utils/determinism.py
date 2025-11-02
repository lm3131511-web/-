from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable


def compute_code_hash(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def project_code_hash(root: Path) -> str:
    files = [p for p in root.rglob("*.py") if "__pycache__" not in p.parts]
    return compute_code_hash(files)
