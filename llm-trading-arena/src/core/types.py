from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class ExecutionStrategy(str, Enum):
    POST_ONLY = "POST_ONLY"
    IOC = "IOC"
    POV = "POV"
    TWAP = "TWAP"


class TradingMode(str, Enum):
    PAPER = "paper"
    SHADOW = "shadow"
    CANARY = "canary"
    LIVE = "live"


class AlertLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(slots=True)
class MarketTick:
    symbol: str
    bid: float
    ask: float
    last_price: float
    ts: float


@dataclass(slots=True)
class OrderRequest:
    symbol: str
    side: OrderSide
    strategy: ExecutionStrategy
    quantity: float
    price: Optional[float]
    ttl_seconds: Optional[int] = None
    client_order_id: Optional[str] = None
