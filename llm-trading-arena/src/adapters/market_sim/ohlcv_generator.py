from __future__ import annotations

import itertools
from typing import Dict, Iterator


def synthetic_ticks(symbols: list[str]) -> Iterator[Dict[str, float]]:
    for idx in itertools.count():
        base = 100 + idx * 0.01
        yield {symbol: base + i for i, symbol in enumerate(symbols)}
