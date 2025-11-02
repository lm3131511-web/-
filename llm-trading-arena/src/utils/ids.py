from __future__ import annotations

import hashlib


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
