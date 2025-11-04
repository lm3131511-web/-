from __future__ import annotations

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


def render_vars(
    market_snapshot: Dict[str, Any],
    limits: Dict[str, Any],
    regime: str,
    risk_level: float,
) -> str:
    payload: Dict[str, Any] = {}
    for key in _ALLOWED_KEYS:
        payload[key] = _coerce_value(key, market_snapshot.get(key, _ALLOWED_KEYS[key]))
    payload["regime"] = regime
    payload["risk_level"] = float(risk_level)

    lines: list[str] = []
    for key in _ALLOWED_KEYS:
        value = payload[key]
        if isinstance(value, float):
            lines.append(f"{key}: {value:.6f}")
        else:
            lines.append(f"{key}: {value}")
    lines.append(f"regime: {payload['regime']}")
    lines.append(f"risk_level: {payload['risk_level']:.4f}")
    lines.append("limits:")
    for name, value in limits.items():
        lines.append(f"  {name}: {value}")
    return "\n".join(lines)


__all__ = ["render_vars"]
