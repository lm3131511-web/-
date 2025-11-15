#!/usr/bin/env python3
"""Validate Codex configuration files."""

from __future__ import annotations

import sys
from pathlib import Path

try:  # pragma: no cover - dependency guard for offline envs
    import yaml  # type: ignore  # noqa: F401
except Exception as exc:  # pragma: no cover - CLI surface
    raise SystemExit(
        "PyYAML не установлен. В Docker-образе он ставится автоматически. "
        "Локально установите PyYAML или используйте оффлайн-режим с колёсами. "
        f"Подробности: {exc}"
    )

from codex.config.loader import load_settings, resolve_config_dir


def main() -> int:
    config_dir = resolve_config_dir()
    if not config_dir.is_dir():
        print(
            "Конфиги не найдены. Укажите CODEX_CONFIG_DIR или скопируйте папку configs в образ.",
            file=sys.stderr,
        )
        return 2

    base_path = config_dir / "base.yaml"
    if not base_path.is_file():
        print(f"Не найден base.yaml по пути {base_path}.", file=sys.stderr)
        return 3
    errors = []
    try:
        load_settings(base_path)
    except Exception as exc:  # pragma: no cover - CLI surface
        errors.append((base_path.name, str(exc)))
    for path in sorted(config_dir.glob("*.yaml")):
        if path.name == "base.yaml":
            continue
        try:
            load_settings(base_path, path)
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
