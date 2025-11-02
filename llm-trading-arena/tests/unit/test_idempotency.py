from src.utils.ids import decision_idempotency_key


def test_decision_idempotency_key_stable() -> None:
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
