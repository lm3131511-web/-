from __future__ import annotations

import hashlib
import time


def decision_idempotency_key(
    *,
    prefix: str,
    symbol: str,
    side: str,
    strategy: str,
    ttl: int | None,
    price: float,
    size_frac: float,
) -> str:
    payload = f"{prefix}{symbol}:{side}:{strategy}:{ttl or 0}:{price:.6f}:{size_frac:.6f}"
    return hashlib.sha256(payload.encode()).hexdigest()


def client_order_id(
    *,
    prefix: str,
    symbol: str,
    side: str,
    price: float,
    size_frac: float,
    ttl: int | None,
) -> str:
    seed = f"{symbol}:{side}:{price:.6f}:{size_frac:.6f}:{ttl or 0}".encode()
    digest = hashlib.sha256(seed).hexdigest()[:8]
    return f"{prefix}{int(time.time() * 1000)}-{digest}"
