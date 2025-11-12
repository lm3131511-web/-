from src.utils.ids import decision_idempotency_key, client_order_id


def test_idempotency_key_deterministic() -> None:
    key1 = decision_idempotency_key(
        prefix="arena-",
        symbol="BTCUSDT",
        side="BUY",
        strategy="POST_ONLY",
        ttl=60,
        price=100.123456,
        size_frac=0.123456,
    )
    key2 = decision_idempotency_key(
        prefix="arena-",
        symbol="BTCUSDT",
        side="BUY",
        strategy="POST_ONLY",
        ttl=60,
        price=100.123456,
        size_frac=0.123456,
    )
    assert key1 == key2


def test_client_order_id_format() -> None:
    client_id = client_order_id(
        prefix="arena-",
        symbol="ETHUSDT",
        side="SELL",
        price=50.0,
        size_frac=0.01,
        ttl=30,
    )
    assert client_id.startswith("arena-")
    assert "-" in client_id
