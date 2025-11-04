from __future__ import annotations

import json
from typing import Any, Dict

_ALLOWED_KEYS = {
    "spread_bps": 0.0,
    "depth_usd_top": 0.0,
    "imbalance": 0.0,
    "micro_price_delta": 0.0,
    "micro_volatility_q": 0.0,
    "last_trades_summary": "n/a",
    "on_demand_features_count": 0,
}


def _coerce_value(name: str, value: Any) -> Any:
    if name in {"last_trades_summary"}:
        return str(value) if value is not None else "n/a"
    if name == "on_demand_features_count":
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
    try:
        return float(value)
    except (TypeError, ValueError):
        return _ALLOWED_KEYS[name]


def _normalise_limit_value(value: Any) -> Any:
    if isinstance(value, (int, float, str, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_normalise_limit_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalise_limit_value(val) for key, val in value.items()}
    return str(value)


def render_vars(
    market_snapshot: Dict[str, Any],
    limits: Dict[str, Any],
    regime: str,
    risk_level: float,
) -> str:
    market_window: Dict[str, Any] = {}
    for key in _ALLOWED_KEYS:
        market_window[key] = _coerce_value(key, market_snapshot.get(key, _ALLOWED_KEYS[key]))
    payload = {
        "market_window": market_window,
        "regime": regime,
        "risk_level": float(risk_level),
        "limits": {k: _normalise_limit_value(v) for k, v in limits.items()},
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


__all__ = ["render_vars"]
