from __future__ import annotations

from typing import Any

from .binance_spot import BinanceSpotAdapter
from .bybit_unified import BybitUnifiedAdapter


def build_exchange_adapter(config: Any):
    name = (config.get("name") if isinstance(config, dict) else config.name).lower()
    payload = config if isinstance(config, dict) else config.model_dump()
    if name == "bybit_unified":
        return BybitUnifiedAdapter(payload)
    return BinanceSpotAdapter(payload)


__all__ = ["build_exchange_adapter", "BinanceSpotAdapter", "BybitUnifiedAdapter"]
