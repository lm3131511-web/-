from __future__ import annotations

from statistics import pstdev
from typing import Any, Dict, Iterable, Sequence

from ..risk.spread_filter import calculate_spread_bps
from ..utils.time import now_utc_iso


def _extract_price_series(tick: Dict[str, Any]) -> Sequence[float]:
    if "micro_prices" in tick and tick["micro_prices"]:
        return [float(p) for p in tick["micro_prices"]]
    trades = tick.get("trades") or []
    if trades:
        return [float(trade.get("price", 0.0)) for trade in trades]
    history = tick.get("price_window") or []
    return [float(p) for p in history if p is not None]


def _summarize_trades(trades: Iterable[Dict[str, Any]]) -> str:
    trades = list(trades or [])
    if not trades:
        return "no_recent_trades"
    buy = sum(float(t.get("qty", 0.0)) for t in trades if t.get("side", "buy").lower() == "buy")
    sell = sum(float(t.get("qty", 0.0)) for t in trades if t.get("side", "sell").lower() == "sell")
    last_price = trades[-1].get("price")
    return f"n={len(trades)} buy={buy:.4f} sell={sell:.4f} last={last_price}"


def _compute_micro_volatility(prices: Sequence[float]) -> float:
    if len(prices) < 2:
        return 0.0
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    if not deltas:
        return 0.0
    return pstdev(deltas) if len(deltas) > 1 else abs(deltas[0])


def _order_imbalance(tick: Dict[str, Any]) -> float:
    bid_depth = float(tick.get("bid_depth_usd", tick.get("bid_depth", 0.0)))
    ask_depth = float(tick.get("ask_depth_usd", tick.get("ask_depth", 0.0)))
    total = bid_depth + ask_depth
    if total <= 0:
        return 0.0
    return (bid_depth - ask_depth) / total


def build_market_window(tick: Dict[str, Any], *, config: Any) -> Dict[str, float]:
    symbol = tick.get("symbol") or (config.assets.get("tickers") or ["BTCUSDT"])[0]
    bid = float(tick.get("bid") or tick.get("best_bid") or tick.get("bid_price") or tick.get("last_price") or 0.0)
    ask = float(tick.get("ask") or tick.get("best_ask") or tick.get("ask_price") or tick.get("last_price") or 0.0)
    if bid <= 0 and ask > 0:
        bid = ask
    if ask <= 0 and bid > 0:
        ask = bid
    mid = (bid + ask) / 2 if bid and ask else float(tick.get("mid_price") or tick.get("last_price") or bid or ask or 0.0)
    spread_bps = calculate_spread_bps(bid=bid or mid, ask=ask or mid)
    prices = list(_extract_price_series(tick))
    micro_volatility = _compute_micro_volatility(prices)
    last_trades = tick.get("trades") or []
    micro_price_delta = 0.0
    if len(prices) >= 2:
        micro_price_delta = prices[-1] - prices[0]
    elif tick.get("micro_price_delta") is not None:
        micro_price_delta = float(tick.get("micro_price_delta"))
    top_depth_usd = float(
        tick.get("top_depth_usd")
        or config.assets.get("top_depth_usd", {}).get(symbol, 1_000_000.0)
    )
    volatility = float(tick.get("volatility", micro_volatility))
    risk_state = float(tick.get("risk_state", 0.0))
    risk_level = float(tick.get("risk_level", abs(risk_state)))

    snapshot = {
        "symbol": symbol,
        "bid": bid,
        "ask": ask,
        "mid_price": mid,
        "spread_bps": spread_bps,
        "top_depth_usd": top_depth_usd,
        "volatility": volatility,
        "micro_volatility_q": micro_volatility,
        "micro_price_delta": micro_price_delta,
        "order_imbalance": _order_imbalance(tick),
        "risk_state": risk_state,
        "risk_level": risk_level,
        "last_trades_summary": _summarize_trades(last_trades),
        "on_demand_features_count": int(tick.get("on_demand_features_count", 0)),
        "ts_utc": tick.get("ts_utc", now_utc_iso()),
    }
    return snapshot
