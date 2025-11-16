#!/usr/bin/env python3
"""Simple alert debouncer to avoid paging storms."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

STATE_SCHEMA_VERSION = 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("message", help="Alert payload to emit if the debounce window has elapsed")
    parser.add_argument(
        "--state-file",
        default="/tmp/codex_alert_state.json",
        help="Path used to persist debounce state (default: %(default)s)",
    )
    parser.add_argument(
        "--window", type=int, default=300, help="Minimum number of seconds between identical alerts"
    )
    return parser.parse_args(argv)


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": STATE_SCHEMA_VERSION, "alerts": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"version": STATE_SCHEMA_VERSION, "alerts": {}}
    if data.get("version") != STATE_SCHEMA_VERSION:
        return {"version": STATE_SCHEMA_VERSION, "alerts": {}}
    return data


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def should_emit(state: dict[str, Any], message: str, window: int) -> bool:
    now = int(time.time())
    alerts = state.setdefault("alerts", {})
    last = alerts.get(message)
    if last is None or now - int(last) >= window:
        alerts[message] = now
        return True
    return False


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    state_path = Path(args.state_file)
    state = load_state(state_path)
    if should_emit(state, args.message, args.window):
        print(args.message)
        save_state(state_path, state)
        return 0
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
