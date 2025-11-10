from src.utils.ids import decision_idempotency_key


def test_idempotency_changes_with_price_and_size() -> None:
    base = decision_idempotency_key(
        prefix="arena-",
        symbol="BTCUSDT",
        side="BUY",
        strategy="POST_ONLY",
        ttl=60,
        price=100.123456,
        size_frac=0.01,
    )
    changed_price = decision_idempotency_key(
        prefix="arena-",
        symbol="BTCUSDT",
        side="BUY",
        strategy="POST_ONLY",
        ttl=60,
        price=100.123556,
        size_frac=0.01,
    )
    changed_size = decision_idempotency_key(
        prefix="arena-",
        symbol="BTCUSDT",
        side="BUY",
        strategy="POST_ONLY",
        ttl=60,
        price=100.123456,
        size_frac=0.02,
    )
    assert base != changed_price
    assert base != changed_size
    repeat = decision_idempotency_key(
        prefix="arena-",
        symbol="BTCUSDT",
        side="BUY",
        strategy="POST_ONLY",
        ttl=60,
        price=100.123456,
        size_frac=0.01,
    )
    assert base == repeat
