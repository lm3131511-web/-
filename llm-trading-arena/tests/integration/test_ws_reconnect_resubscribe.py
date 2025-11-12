from src.adapters.exchange.binance_spot import BinanceSpotAdapter


def test_metrics_expose_ws_counters() -> None:
    adapter = BinanceSpotAdapter(
        {
            "base_url": "https://api.binance.com",
            "recv_window_ms": 5000,
            "precision_cache_ttl_sec": 1,
        }
    )
    snapshot = adapter.metrics_snapshot()
    assert "ws_reconnects_total" in snapshot
    assert "ws_resubscribe_failures_total" in snapshot
