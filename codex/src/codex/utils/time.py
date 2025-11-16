from __future__ import annotations

from datetime import datetime, timezone, time
from typing import Tuple


UTC = timezone.utc


def utc_now() -> datetime:
    """Return timezone-aware UTC now."""
    return datetime.now(tz=UTC)


def parse_window(window: str) -> Tuple[time, time]:
    """Parse a HH:MM-HH:MMZ window into naive time bounds."""
    if not window.endswith("Z") or "-" not in window:
        raise ValueError(f"Invalid window format: {window}")
    start_s, end_s = window[:-1].split("-")
    start = time.fromisoformat(start_s)
    end = time.fromisoformat(end_s)
    return start, end


def is_within_window(ts: datetime, window: str) -> bool:
    """Return True when the UTC timestamp falls within the deny window."""
    start, end = parse_window(window)
    t = ts.timetz().replace(tzinfo=None)
    if start <= end:
        return start <= t <= end
    # window wraps midnight
    return t >= start or t <= end
