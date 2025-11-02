from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from src.vendor.dotenv import load_dotenv

from ..adapters.exchange.binance_spot import BinanceSpotAdapter, BinanceCreds
from ..alerts.sink import build_alert_sink
from ..config.loader import load_config
from ..config.validators import validate_config
from ..core.contracts import (
    AnalystResponse,
    AuditInfo,
    FinalDecision,
    RiskGateApproval,
    Signal,
)
from ..core.contracts import AggregationResult
from ..core.types import ExecutionStrategy, OrderRequest, OrderSide, TradingMode
from ..exec.planner import ExecutionPlanner
from ..exec.sizing import compute_adv_fraction
from ..features.core_features import build_core_features
from ..features.on_demand_features import build_on_demand_features
from ..features.regime_detection import detect_regime
from ..llm.aggregator import AggregationError, aggregate_responses
from ..llm.stages import StageRunner, build_stage_runners
from ..monitoring.exporter_http import start_http_exporter
from ..monitoring.health import HealthSnapshot
from ..monitoring.metrics import GLOBAL_METRICS
from ..risk.gate import CooldownConfig, MarketLimits, PnLBreakers, RiskConfig, RiskGate, RiskLimits, CircuitBreakers
from ..risk.spread_filter import calculate_spread_bps
from .startup_checks import ensure_contract_schemas


@dataclass
class StoragePaths:
    jsonl_path: Path
    sqlite_path: Path


class TradingArena:
    def __init__(self, config: Any, *, dry_run: bool) -> None:
        self.config = config
        self.dry_run = dry_run
        self.mode = config.mode
        self.fail_closed = False
        self.adapter = BinanceSpotAdapter(config.exchange.model_dump())
        self.alert_sink = build_alert_sink(
            config.monitoring.alert_sink,
            config.monitoring.model_dump(),
            config.telegram.model_dump(),
        )
        self.storage_paths = self._resolve_storage_paths(config)
        self._sqlite_conn: sqlite3.Connection | None = None
        self._http_server = None
        self._stage_runners: list[StageRunner] = []
        self._planner = ExecutionPlanner(
            config.execution.model_dump(),
        )
        self._last_market_snapshot: Dict[str, Any] | None = None
        self._risk_gate = RiskGate(
            RiskConfig(
                limits=RiskLimits(**config.risk_gate.limits),
                market=MarketLimits(**config.risk_gate.market),
                pnl_breaker=PnLBreakers(**config.risk_gate.pnl_breaker),
                cooldowns=CooldownConfig(**config.risk_gate.cooldowns),
                circuit_breakers=CircuitBreakers(**config.risk_gate.circuit_breakers),
            ),
            sell_enabled=config.sell_enabled,
        )
        self._health = HealthSnapshot(
            ready=False,
            schema_version=int(config.schemas.get("version", 1)),
            last_snapshot_id="",
            mode=config.mode,
            venue=config.exchange.name,
        )

    @staticmethod
    def _resolve_storage_paths(config: Any) -> StoragePaths:
        extra = getattr(config, "model_extra", {}) or {}
        base_dir = Path(extra.get("storage_dir", "."))
        jsonl_path = base_dir / extra.get("decision_log", "decisions.jsonl")
        sqlite_path = base_dir / extra.get("sqlite_path", "arena.sqlite3")
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        return StoragePaths(jsonl_path=jsonl_path, sqlite_path=sqlite_path)

    async def initialize(self) -> None:
        ensure_contract_schemas()
        await self.adapter.start()
        self._sqlite_conn = sqlite3.connect(self.storage_paths.sqlite_path)
        with Path(__file__).resolve().parents[1].joinpath("storage", "sqlite_schema.sql").open("r", encoding="utf-8") as ddl:
            self._sqlite_conn.executescript(ddl.read())
        self._sqlite_conn.commit()
        self._stage_runners = build_stage_runners(
            {name: cfg.model_dump() for name, cfg in self.config.llm.stages.items()},
            self.config.llm.token_budget_per_tick,
        )
        self._http_server = start_http_exporter(
            port=self.config.monitoring.metrics_port,
            health_supplier=lambda: self._health,
        )
        self._health.ready = True

    async def stop(self) -> None:
        await self.adapter.stop()
        if self._sqlite_conn:
            self._sqlite_conn.close()
            self._sqlite_conn = None
        if self._http_server:
            self._http_server.shutdown()
            self._http_server.server_close()
            self._http_server = None

    async def run_once(self) -> FinalDecision:
        market_data = await self.adapter.get_next_data()
        self._last_market_snapshot = market_data
        features = build_core_features(market_data)
        features.update(build_on_demand_features(market_data, self.config.llm.max_on_demand_features))
        regime = detect_regime({"volatility": market_data.get("volatility", 0.01)})

        responses: list[AnalystResponse] = []
        for runner in self._stage_runners:
            response = await runner.run(market_data)
            responses.append(response)

        try:
            aggregation = aggregate_responses(
                responses,
                tau=self.config.llm.aggregator_tau,
                max_budget_usd=self.config.llm.budget_usd_per_min,
            )
        except AggregationError as exc:
            self.fail_closed = True
            risk = RiskGateApproval(approved=False, reason=str(exc))
            decision = self._build_decision(
                status="rejected",
                reason=str(exc),
                aggregation=None,
                signal=None,
                risk=risk,
                execution=None,
            )
            await self._persist_decision(decision)
            return decision

        side = "BUY" if aggregation.p_final >= 0.5 else "SELL"
        signal = Signal(
            symbol=self.config.assets["tickers"][0],
            side=side,
            strength=aggregation.p_final,
            z_score=aggregation.p_final * 2 - 1,
            p_final=aggregation.p_final,
            uncertainty=aggregation.uncertainty,
            reasoning=f"regime={regime}",
        )
        spread_bps = calculate_spread_bps(
            bid=market_data.get("bid", 100.0),
            ask=market_data.get("ask", 100.1),
        )
        risk = self._risk_gate.approve(
            spread_bps=spread_bps,
            is_buy=side == "BUY",
            losses_pct=0.0,
        )
        if not risk.approved:
            if risk.circuit_breaker_tripped or risk.pnl_breaker_tripped:
                self.fail_closed = True

        execution = None
        if risk.approved and not self.fail_closed:
            adv_fraction = compute_adv_fraction(
                aggregation.p_final,
                aggregation.uncertainty,
                max_fraction=self.config.risk_gate.sizing.get("pos_cap_per_asset_pct", 1.0) / 100,
            )
            execution = self._planner.plan(signal, adv_fraction=adv_fraction)

        status = "approved" if execution and risk.approved and not self.fail_closed else "rejected"
        reason = None if status == "approved" else (risk.reason or "fail_closed")
        decision = self._build_decision(
            status=status,
            reason=reason,
            aggregation=aggregation,
            signal=signal,
            risk=risk,
            execution=execution,
        )
        await self._persist_decision(decision)
        await self._emit_alert(decision)
        if status == "approved" and self.mode in {TradingMode.CANARY.value, TradingMode.LIVE.value} and not self.dry_run:
            await self._execute_plan(decision)
        return decision

    async def run_forever(self) -> None:
        while True:
            await self.run_once()

    def _build_decision(
        self,
        *,
        status: str,
        reason: str | None,
        aggregation: AggregationResult | None,
        signal: Signal | None,
        risk: RiskGateApproval,
        execution: Any,
    ) -> FinalDecision:
        payload = {
            "status": status,
            "reason": reason,
            "aggregation": aggregation.model_dump() if aggregation else None,
            "signal": signal.model_dump() if signal else None,
            "risk": risk.model_dump(),
            "execution": execution.model_dump() if execution else None,
        }
        serialized = json.dumps(payload, sort_keys=True)
        idem = hashlib.sha256(serialized.encode()).hexdigest()
        audit = AuditInfo(
            idempotency_key=idem,
            created_at=time.time(),
            snapshot_id=str(int(time.time())),
            mode=self.mode,
        )
        self._health.last_snapshot_id = audit.snapshot_id
        return FinalDecision(
            status=status,  # type: ignore[arg-type]
            reason=reason,
            analyst=None,
            aggregation=aggregation or AggregationResult(
                contributors=[], p_final=0.0, uncertainty=1.0, tau=0.0, budget_spent_usd=0.0
            ),
            signal=signal
            or Signal(
                symbol=self.config.assets["tickers"][0],
                side="HOLD",
                strength=0.0,
                z_score=0.0,
                p_final=0.0,
                uncertainty=1.0,
                reasoning="no-signal",
            ),
            risk_gate=risk,
            execution=execution,
            audit=audit,
        )

    async def _persist_decision(self, decision: FinalDecision) -> None:
        record = decision.model_dump(mode="json")
        with self.storage_paths.jsonl_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        if not self._sqlite_conn:
            raise RuntimeError("sqlite not initialized")
        self._sqlite_conn.execute(
            "INSERT OR REPLACE INTO final_decisions (idempotency_key, payload, created_at) VALUES (?, ?, ?)",
            (decision.audit.idempotency_key, json.dumps(record, sort_keys=True), decision.audit.created_at),
        )
        self._sqlite_conn.commit()
        GLOBAL_METRICS.inc_metric(f"decisions_{decision.status}")

    async def _emit_alert(self, decision: FinalDecision) -> None:
        if decision.status != "approved":
            return
        leg = decision.execution.legs[0] if decision.execution else None
        plan_text = "n/a"
        if leg:
            plan_text = f"{leg.strategy} @ {leg.price or 'MKT'} (TTL={leg.ttl_seconds}s)"
        message = (
            "[LLM Trading Arena • APPROVED]\n"
            f"Asset: {decision.signal.symbol}\n"
            f"Side: {decision.signal.side}\n"
            f"Size: {decision.signal.strength:.2%} ADV\n"
            f"Plan: {plan_text}\n"
            f"p_final={decision.signal.p_final:.2f}  U={decision.signal.uncertainty:.2f}  τ={decision.aggregation.tau:.1f}\n"
            f"mode={self.mode}  snapshot={decision.audit.snapshot_id}"
        )
        await self.alert_sink.publish(message, level=self.config.monitoring.alert_min_level)

    async def _execute_plan(self, decision: FinalDecision) -> None:
        creds = BinanceCreds(
            api_key=os.environ.get(self.config.exchange.api_key_env, ""),
            api_secret=os.environ.get(self.config.exchange.api_secret_env, ""),
        )
        if not creds.api_key or not creds.api_secret:
            return
        for leg in decision.execution.legs:
            request = OrderRequest(
                symbol=leg.symbol,
                side=OrderSide(leg.side),
                strategy=ExecutionStrategy(leg.strategy),
                quantity=leg.quantity,
                price=(
                    float(leg.price)
                    if leg.price is not None
                    else float(
                        (self._last_market_snapshot or {}).get(
                            "ask",
                            (self._last_market_snapshot or {}).get("last_price", 0.0),
                        )
                    )
                ),
                ttl_seconds=leg.ttl_seconds,
                client_order_id=decision.audit.idempotency_key[:20],
            )
            await self.adapter.place_order(request, creds)


def run_pipeline_cli(*, mode: str, config_path: str, dry_run: bool) -> None:
    load_dotenv()
    config = load_config(config_path)
    validate_config(config)
    arena = TradingArena(config, dry_run=dry_run or mode in {"paper", "shadow"})

    async def runner() -> None:
        await arena.initialize()
        try:
            await arena.run_once()
        finally:
            await arena.stop()

    asyncio.run(runner())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--dry_run", action="store_true")
    args = parser.parse_args()
    run_pipeline_cli(mode=args.mode, config_path=args.config, dry_run=args.dry_run)
