from __future__ import annotations

import argparse
import asyncio
import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

from src.vendor.dotenv import load_dotenv

from ..adapters.exchange.binance_spot import BinanceCreds, BinanceSpotAdapter
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
from ..exec.planner import ExecutionPlanner, InfeasiblePlan
from ..exec.sizing import compute_final_fraction
from ..features.core_features import build_core_features
from ..features.on_demand_features import build_on_demand_features
from ..features.regime_detection import detect_regime
from ..llm.aggregator import AggregationError, aggregate_responses
from ..llm.stages import StageRunner, build_stage_runners
from ..monitoring.exporter_http import start_http_exporter
from ..monitoring.health import HealthSnapshot
from ..monitoring.metrics import GLOBAL_METRICS
from ..risk.gate import (
    CooldownConfig,
    MarketLimits,
    PnLBreakers,
    RiskConfig,
    RiskGate,
    RiskLimits,
    CircuitBreakers,
)
from ..risk.spread_filter import calculate_spread_bps
from ..utils.determinism import project_code_hash
from ..utils.ids import decision_idempotency_key
from ..utils.logrotate import ensure_parent, rotate_if_big
from ..utils.time import now_utc_iso
from .startup_checks import ensure_contract_schemas


@dataclass
class StoragePaths:
    decisions: Path
    execution: Path
    audit: Path
    alerts: Path
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
        self._planner = ExecutionPlanner(config.execution.model_dump())
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
        self._code_hash = project_code_hash(Path(__file__).resolve().parents[1])
        self._seed = int(os.environ.get("ARENA_SEED", "2024"))
        self._kill_switch_state = os.environ.get("KILL_SWITCH", "OFF").upper()

    @staticmethod
    def _resolve_storage_paths(config: Any) -> StoragePaths:
        base_dir = Path(config.storage_dir)
        decisions = Path(config.logging.paths.decisions)
        execution = Path(config.logging.paths.execution)
        audit = Path(config.logging.paths.audit)
        alerts = Path(config.logging.paths.alerts)
        sqlite_path = base_dir / config.sqlite_path
        for path in (decisions, execution, audit, alerts, sqlite_path):
            ensure_parent(path)
        return StoragePaths(
            decisions=decisions,
            execution=execution,
            audit=audit,
            alerts=alerts,
            sqlite_path=sqlite_path,
        )

    async def initialize(self) -> None:
        ensure_contract_schemas()
        rotate_if_big(self.storage_paths.decisions)
        rotate_if_big(self.storage_paths.execution)
        rotate_if_big(self.storage_paths.audit)
        rotate_if_big(self.storage_paths.alerts)
        await self.adapter.start()
        self._sqlite_conn = sqlite3.connect(self.storage_paths.sqlite_path)
        ddl_path = Path(__file__).resolve().parents[1].joinpath("storage", "sqlite_schema.sql")
        with ddl_path.open("r", encoding="utf-8") as ddl:
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
        self._health.kill_switch_state = self._kill_switch_state

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
        if self._kill_switch_state != "OFF":
            self.fail_closed = True
        market_data = await self.adapter.get_next_data()
        snapshot = self._compose_market_snapshot(market_data)
        features = build_core_features(snapshot)
        features.update(
            build_on_demand_features(snapshot, self.config.llm.max_on_demand_features)
        )
        regime = detect_regime({"volatility": snapshot["volatility"]})

        responses: list[AnalystResponse] = []
        for runner in self._stage_runners:
            response = await runner.run(snapshot)
            responses.append(response)

        try:
            aggregation = aggregate_responses(
                responses,
                tau=self.config.llm.aggregator_tau,
                budget_usd_per_min=self.config.llm.budget_usd_per_min,
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

        primary_response = self._select_primary_response(responses, aggregation)
        signal = self._build_signal(primary_response, aggregation)
        spread_bps = snapshot["spread_bps"]
        risk = self._risk_gate.approve(
            spread_bps=spread_bps,
            is_buy=signal.side == "BUY",
            losses_pct=0.0,
        )
        if not risk.approved and (
            risk.circuit_breaker_tripped or risk.pnl_breaker_tripped or risk.reason in {"pnl_breaker", "loss_limit"}
        ):
            self.fail_closed = True

        execution = None
        if (
            risk.approved
            and not self.fail_closed
            and signal.final_size_frac > 0
            and primary_response.strategy in self.config.execution.strategies
        ):
            notional_usd = signal.final_size_frac * self._adv_usd(signal.symbol)
            try:
                execution = self._planner.plan(
                    signal=signal,
                    market_snapshot=snapshot,
                    price_band_bps=(
                        primary_response.price_band_hint.width_bps
                        if primary_response.price_band_hint
                        else None
                    ),
                    ttl_hint=primary_response.ttl_hint_sec,
                    notional_usd=notional_usd,
                )
            except InfeasiblePlan:
                risk = RiskGateApproval(
                    approved=False,
                    reason="execution_infeasible",
                    limit_check=risk.limit_check,
                    cooldown_active=risk.cooldown_active,
                    circuit_breaker_tripped=risk.circuit_breaker_tripped,
                    pnl_breaker_tripped=risk.pnl_breaker_tripped,
                )

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
        if (
            status == "approved"
            and self.mode in {TradingMode.CANARY.value, TradingMode.LIVE.value}
            and not self.dry_run
        ):
            await self._execute_plan(decision, snapshot)
        return decision

    async def run_forever(self) -> None:
        while True:
            await self.run_once()

    def _compose_market_snapshot(self, data: Dict[str, Any]) -> Dict[str, float]:
        bid = float(data.get("bid", data.get("last_price", 0.0)))
        ask = float(data.get("ask", data.get("last_price", 0.0)))
        mid = (bid + ask) / 2 if bid and ask else float(data.get("mid", 0.0))
        volatility = float(data.get("volatility", 0.01))
        spread_bps = calculate_spread_bps(bid=bid, ask=ask)
        drift = float(data.get("drift", data.get("price_change", 0.0)))
        micro_delta = float(data.get("micro_price_delta", drift / (mid or 1.0)))
        risk_state = float(data.get("risk_state", 0.0))
        snapshot = {
            "bid": bid,
            "ask": ask,
            "mid": mid,
            "last_price": float(data.get("last_price", mid)),
            "volatility": volatility,
            "spread_bps": spread_bps,
            "drift": drift,
            "micro_price_delta": micro_delta,
            "risk_state": risk_state,
        }
        return snapshot

    def _select_primary_response(
        self, responses: Iterable[AnalystResponse], aggregation: AggregationResult
    ) -> AnalystResponse:
        weights = aggregation.weights
        return max(
            responses,
            key=lambda response: weights.get(response.stage, 0.0) * response.confidence,
        )

    def _build_signal(self, response: AnalystResponse, aggregation: AggregationResult) -> Signal:
        symbol = self.config.assets["tickers"][0]
        side = response.direction if response.direction != "FLAT" else "FLAT"
        kelly_base = max(0.0, aggregation.p_final * 2 - 1)
        safety_multiplier = max(0.1, 1 - aggregation.uncertainty)
        max_cap = self.config.risk_gate.sizing.get("pos_cap_per_asset_pct", 1.0) / 100
        final_fraction = (
            0.0
            if side == "FLAT"
            else compute_final_fraction(
                size_hint_frac=response.size_hint_frac,
                kelly_base=kelly_base,
                safety_multiplier=safety_multiplier,
                max_cap=max_cap,
            )
        )
        return Signal(
            symbol=symbol,
            side=side,
            strategy=response.strategy,
            kelly_base=kelly_base,
            safety_multiplier=safety_multiplier,
            final_size_frac=final_fraction,
            p_final=aggregation.p_final,
            uncertainty=aggregation.uncertainty,
            reasoning=f"regime={aggregation.degradation_mode}",
        )

    def _adv_usd(self, symbol: str) -> float:
        table = self.config.assets.get("adv_usd_table", {})
        return float(table.get(symbol, 1_000_000.0))

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
        timestamp = now_utc_iso()
        market_price = 0.0
        idempotency = decision_idempotency_key(
            prefix=self.config.order_management.idempotency_prefix,
            symbol=(signal.symbol if signal else self.config.assets["tickers"][0]),
            side=signal.side if signal else "FLAT",
            strategy=signal.strategy if signal else "POST_ONLY",
            ttl=execution.legs[0].ttl_seconds if execution else None,
            price=execution.legs[0].price if execution else market_price,
            size_frac=signal.final_size_frac if signal else 0.0,
        )
        audit = AuditInfo(
            idempotency_key=idempotency,
            ts_utc=timestamp,
            snapshot_id=timestamp.replace("Z", ""),
            mode=self.mode,
            code_hash=self._code_hash,
            seed=self._seed,
            kill_switch_state=self._kill_switch_state,
            degradation_mode=aggregation.degradation_mode if aggregation else "fail",
        )
        self._health.last_snapshot_id = audit.snapshot_id
        self._health.kill_switch_state = self._kill_switch_state
        self._health.breakers = {
            "fail_closed": self.fail_closed,
            "risk_fail": not risk.approved,
        }
        return FinalDecision(
            status=status,  # type: ignore[arg-type]
            reason=reason,
            analyst=None,
            aggregation=
            aggregation
            or AggregationResult(
                contributors=[],
                p_final=0.0,
                uncertainty=1.0,
                tau_used=0.0,
                weights={},
                reliability_scores={},
                budget_spent_usd=0.0,
                budget_left_usd=0.0,
                degradation_mode="fail",
            ),
            signal=
            signal
            or Signal(
                symbol=self.config.assets["tickers"][0],
                side="FLAT",
                strategy="POST_ONLY",
                kelly_base=0.0,
                safety_multiplier=0.0,
                final_size_frac=0.0,
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
        self._write_jsonl(self.storage_paths.decisions, record)
        if decision.execution:
            self._write_jsonl(self.storage_paths.execution, decision.execution.model_dump(mode="json"))
        self._write_jsonl(self.storage_paths.audit, decision.audit.model_dump(mode="json"))
        if not self._sqlite_conn:
            raise RuntimeError("sqlite not initialized")
        self._sqlite_conn.execute(
            "INSERT OR REPLACE INTO decisions (id, ts_utc, asset, status, side, size_frac, strategy, ttl_seconds, snapshot_id, code_hash, idempotency_key) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                decision.audit.idempotency_key,
                decision.audit.ts_utc,
                decision.signal.symbol,
                decision.status,
                decision.signal.side,
                decision.signal.final_size_frac,
                decision.signal.strategy,
                decision.execution.legs[0].ttl_seconds if decision.execution else None,
                decision.audit.snapshot_id,
                decision.audit.code_hash,
                decision.audit.idempotency_key,
            ),
        )
        self._sqlite_conn.commit()
        GLOBAL_METRICS.inc_metric(f"decisions_{decision.status}")
        GLOBAL_METRICS.set_metric("degradation_mode", {
            "full": 0,
            "reduced": 1,
            "minimal": 2,
            "emergency": 3,
        }.get(decision.aggregation.degradation_mode, 4))

    def _write_jsonl(self, path: Path, payload: Dict[str, Any]) -> None:
        rotate_if_big(path)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

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
            f"Size: {decision.signal.final_size_frac:.2%} ADV\n"
            f"Plan: {plan_text}\n"
            f"p_final={decision.signal.p_final:.2f}  U={decision.signal.uncertainty:.2f}  τ={decision.aggregation.tau_used:.1f}\n"
            f"mode={self.mode}  snapshot={decision.audit.snapshot_id}"
        )
        await self.alert_sink.publish(message, level=self.config.monitoring.alert_min_level)
        self._write_jsonl(self.storage_paths.alerts, {"message": message, "ts": now_utc_iso()})

    async def _execute_plan(self, decision: FinalDecision, snapshot: Dict[str, float]) -> None:
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
                price=float(leg.price) if leg.price is not None else snapshot["mid"],
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
