#!/usr/bin/env python3
"""Validate Codex configuration files."""

from __future__ import annotations

import sys
from pathlib import Path

from codex.config.loader import load_settings


def main() -> int:
    base_dir = Path(__file__).resolve().parents[1]
    config_dir = base_dir / "configs"
    errors = []
    for path in config_dir.glob("*.yaml"):
        try:
            load_settings(path)
        except Exception as exc:  # pragma: no cover - CLI surface
            errors.append((path.name, str(exc)))
    if errors:
        for name, err in errors:
            print(f"{name}: {err}")
        return 1
    print("All configurations are valid.")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI guard
    raise SystemExit(main())
