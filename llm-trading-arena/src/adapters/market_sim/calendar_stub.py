from __future__ import annotations

import time


def current_trading_day() -> str:
    return time.strftime("%Y-%m-%d")
