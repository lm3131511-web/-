#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from src.adapters.market_sim.ohlcv_generator import synthetic_ticks


def main() -> None:
    path = Path("synthetic_ticks.jsonl")
    with path.open("w", encoding="utf-8") as handle:
        for idx, tick in zip(range(100), synthetic_ticks(["BTCUSDT", "ETHUSDT"])):
            handle.write(json.dumps({"seq": idx, "tick": tick}) + "\n")


if __name__ == "__main__":
    main()
