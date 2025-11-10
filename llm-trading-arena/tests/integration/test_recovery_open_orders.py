import random
import sqlite3
from pathlib import Path

from src.adapters.exec_sim import simulate_order_execution
from src.core.contracts import ExecutionLeg, ExecutionPlan


def test_simulated_fills_can_persist(tmp_path) -> None:
    plan = ExecutionPlan(
        legs=[
            ExecutionLeg(
                symbol="BTCUSDT",
                side="BUY",
                strategy="POST_ONLY",
                price=100.0,
                quantity=0.5,
                ttl_seconds=60,
            )
        ],
        idempotency_key="decision",
        client_order_id="client",
        strategy="POST_ONLY",
    )
    economics = {
        "stress_slippage_prob": 0.0,
        "normal": {"k_vol_bps": 0.35, "sigma": 0.6},
        "stress": {"k_vol_bps": 0.75, "sigma": 1.2},
    }
    snapshot = {
        "mid_price": 100.0,
        "spread_bps": 2.0,
        "volatility": 0.01,
        "top_depth_usd": 2_000_000.0,
    }
    fills, summary = simulate_order_execution(
        plan,
        snapshot,
        economics,
        decision_id="decision",
        rng=random.Random(5),
    )
    db_path = tmp_path / "fills.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE fills(id TEXT, decision_id TEXT, ts_utc TEXT, asset TEXT, price REAL, qty REAL, fee_usd REAL, slippage_bps REAL)"
    )
    conn.executemany(
        "INSERT INTO fills VALUES(?,?,?,?,?,?,?,?)",
        [
            (
                fill.id,
                fill.decision_id,
                fill.ts_utc,
                fill.asset,
                fill.price,
                fill.qty,
                fill.fee_usd,
                fill.slippage_bps,
            )
            for fill in fills
        ],
    )
    conn.commit()
    rows = list(conn.execute("SELECT decision_id FROM fills"))
    assert rows and rows[0][0] == "decision"
    conn.close()
