from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List
from uuid import uuid4

from ...utils.time import now_utc_iso


@dataclass(slots=True)
class SimulatedFill:
    id: str
    decision_id: str
    ts_utc: str
    asset: str
    price: float
    qty: float
    fee_usd: float
    slippage_bps: float

    def to_record(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "decision_id": self.decision_id,
            "ts_utc": self.ts_utc,
            "asset": self.asset,
            "price": self.price,
            "qty": self.qty,
            "fee_usd": self.fee_usd,
            "slippage_bps": self.slippage_bps,
        }


def create_fill(
    *,
    decision_id: str,
    asset: str,
    price: float,
    qty: float,
    slippage_bps: float,
    fee_rate: float = 0.0004,
) -> SimulatedFill:
    qty = float(qty)
    price = float(price)
    ts_utc = now_utc_iso()
    fee_usd = abs(qty * price) * fee_rate
    return SimulatedFill(
        id=str(uuid4()),
        decision_id=decision_id,
        ts_utc=ts_utc,
        asset=asset,
        price=price,
        qty=qty,
        fee_usd=fee_usd,
        slippage_bps=float(slippage_bps),
    )


def serialize_fills(fills: Iterable[SimulatedFill]) -> List[Dict[str, Any]]:
    return [fill.to_record() for fill in fills]
