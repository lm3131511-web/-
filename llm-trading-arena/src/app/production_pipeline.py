from __future__ import annotations

import argparse
import asyncio
import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from src.vendor.dotenv import load_dotenv

from ..adapters.exchange import build_exchange_adapter
from ..adapters.exchange.binance_spot import BinanceCreds
from ..adapters.exchange.bybit_unified import BybitCreds
from ..adapters.exec_sim import SimulatedFill, simulate_order_execution, serialize_fills
from ..alerts.sink import build_alert_sink
from ..config.loader import load_config
from ..config.validators import validate_config
from ..core.contracts import (
    AggregationResult,
    AnalystResponse,
    AuditInfo,
    ExecutionPlan,
    FinalDecision,
    RiskGateApproval,
    Signal,
)
from ..core.types import ExecutionStrategy, OrderRequest, OrderSide, TradingMode
from ..exec.planner import ExecutionPlanner, InfeasiblePlan
from ..features.core_features import build_core_features
from ..features.market_window import build_market_window
from ..features.on_demand_features import build_on_demand_features
from ..features.regime_detection import detect_regime
from ..llm.aggregator import AggregationError, aggregate_responses
from ..llm.cost_control import BudgetManager
from ..llm.degradation import DegradationController
from ..llm.stages import build_stage_runners
from ..monitoring.exporter_http import start_http_exporter
from ..monitoring.health import HealthSnapshot
from ..monitoring.metrics import GLOBAL_METRICS
from ..risk.gate import (
    CircuitBreakers,
    CooldownConfig,
    MarketLimits,
    PnLBreakers,
    RiskConfig,
    RiskGate,
    RiskLimits,
)
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
        self.mode = TradingMode(config.mode)
        self.adapter = build_exchange_adapter(config.exchange)
        self.storage_paths = self._resolve_storage_paths(config)
        self._sqlite_conn: sqlite3.Connection | None = None
        self._http_server = None
        stage_limits = {
            "ttl_sec_range": list(config.execution.ttl_sec_range),
            "max_spread_bps": config.execution.max_spread_bps,
            "max_on_demand_features": config.llm.max_on_demand_features,
        }
        self._stage_runners = build_stage_runners(config.llm, limits=stage_limits)
        self._budget_manager = BudgetManager(config.llm, config.mode)
        self._degradation = DegradationController(config.llm.degradation)
        self._planner = ExecutionPlanner(
            execution_cfg=config.execution.model_dump(),
            order_cfg=config.order_management.model_dump(),
        )
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
        self.alert_sink = build_alert_sink(
            config.monitoring.alert_sink,
            config.monitoring.model_dump(),
            config.telegram.model_dump(),
            queue_path=self.storage_paths.alerts,
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
        self._kill_callback_triggered = False

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
            rotate_if_big(path)
        return StoragePaths(
            decisions=decisions,
            execution=execution,
            audit=audit,
            alerts=alerts,
            sqlite_path=sqlite_path,
        )

    async def initialize(self) -> None:
        ensure_contract_schemas()
        await self.adapter.start()
        self._sqlite_conn = sqlite3.connect(self.storage_paths.sqlite_path)
        ddl_path = Path(__file__).resolve().parents[1].joinpath("storage", "sqlite_schema.sql")
        with ddl_path.open("r", encoding="utf-8") as ddl:
            self._sqlite_conn.executescript(ddl.read())
        self._sqlite_conn.commit()
        monitoring_http = self.config.monitoring.http
        auth_token = None
        if monitoring_http.auth_token_env:
            auth_token = os.environ.get(monitoring_http.auth_token_env)
        self._http_server = start_http_exporter(
            bind=monitoring_http.bind,
            port=self.config.monitoring.metrics_port,
            health_supplier=lambda: self._health,
            kill_callback=self._engage_kill_switch,
            auth_token=auth_token,
            kill_rate_limit_per_min=monitoring_http.kill_rate_limit_per_min,
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
        if self._kill_switch_state != "OFF" or self._kill_callback_triggered:
            self._kill_switch_state = "ON"
            self._health.kill_switch_state = self._kill_switch_state
            raise RuntimeError("kill switch engaged")

        tick = await self.adapter.get_next_data()
        self._enforce_time_sync()
        snapshot = self._compose_market_snapshot(tick)
        regime, risk_level = detect_regime(snapshot)
        budget_snapshot = self._budget_manager.compute_budget(regime=regime, risk_level=risk_level)
        enriched_snapshot = {**snapshot}
        enriched_snapshot.update(build_core_features(snapshot))
        enriched_snapshot.update(build_on_demand_features(snapshot, self.config.llm.max_on_demand_features))

        responses = await self._run_stages(enriched_snapshot, regime=regime, risk_level=risk_level)
        try:
            aggregation = aggregate_responses(
                responses,
                tau=self.config.llm.aggregator_tau,
                reliability_lambda=self.config.llm.reliability.lambda_,
                budget_limit_usd=budget_snapshot.effective_budget_usd,
                degradation_mode=self._degradation.state.mode,
            )
        except AggregationError as exc:
            return await self._finalize_decision(
                responses=responses,
                aggregation=None,
                signal=None,
                approval=RiskGateApproval(
                    approved=False,
                    reason=f"aggregation_error:{exc}",
                    limit_check={},
                    cooldown_active=False,
                    circuit_breaker_tripped=False,
                    pnl_breaker_tripped=False,
                    infeasible=True,
                ),
                execution=None,
                snapshot=snapshot,
                regime=regime,
            )

        budget_left_pct = 0.0
        if budget_snapshot.base_budget_usd > 0:
            budget_left_pct = aggregation.budget_left_usd / budget_snapshot.base_budget_usd
        new_mode = self._degradation.update(
            uncertainty=aggregation.uncertainty, budget_left_pct=budget_left_pct
        )
        if new_mode != aggregation.degradation_mode:
            aggregation = aggregation.model_copy(update={"degradation_mode": new_mode})
        GLOBAL_METRICS.set_degradation(new_mode, aggregation.uncertainty)

        primary = self._select_primary_response(responses)
        signal = self._build_signal(
            primary=primary,
            aggregation=aggregation,
            regime=regime,
            symbol=snapshot["symbol"],
        )
        spread_bps = snapshot.get("spread_bps", 0.0)
        approval = self._risk_gate.approve(
            spread_bps=spread_bps,
            is_buy=signal.side == "BUY",
            losses_pct=0.0,
            infeasible=signal.final_size_frac <= 0,
        )
        execution: ExecutionPlan | None = None
        if approval.approved:
            try:
                execution = self._planner.plan(
                    signal=signal,
                    market_snapshot=snapshot,
                    price_band_hint=primary.price_band_hint.width_bps if primary.price_band_hint else None,
                    ttl_hint=primary.ttl_hint_sec,
                )
            except InfeasiblePlan:
                approval = approval.model_copy(
                    update={"approved": False, "reason": "planner_infeasible", "infeasible": True}
                )

        decision = await self._finalize_decision(
            responses=responses,
            aggregation=aggregation,
            signal=signal,
            approval=approval,
            execution=execution,
            snapshot=snapshot,
            regime=regime,
        )
        if decision.status == "approved" and decision.execution:
            await self._handle_execution(decision, snapshot)
        return decision

    async def run_forever(self) -> None:
        try:
            while True:
                await self.run_once()
        except asyncio.CancelledError:  # pragma: no cover - cooperative shutdown
            return

    def _engage_kill_switch(self) -> None:
        self._kill_callback_triggered = True
        self._kill_switch_state = "ON"
        self._health.kill_switch_state = "ON"

    async def _run_stages(
        self,
        snapshot: Dict[str, float],
        *,
        regime: str,
        risk_level: float,
    ) -> List[AnalystResponse]:
        results: List[AnalystResponse] = []
        for runner in self._stage_runners:
            result = await runner.run(snapshot, regime=regime, risk_level=risk_level)
            estimated_cost = (result.prompt_tokens + result.completion_tokens) / 1000.0 * 0.002
            if not self._budget_manager.register_provider_spend(result.stage, estimated_cost):
                GLOBAL_METRICS.inc_metric("budget_sentry_hits")
                result = result.model_copy(
                    update={
                        "direction": "FLAT",
                        "strategy": "POST_ONLY",
                        "confidence": 0.0,
                        "urgency": 0.0,
                        "size_hint_frac": 0.0,
                        "reliability": 0.0,
                        "reasoning": "budget_guard_triggered",
                    }
                )
            results.append(result)
        return results

    def _select_primary_response(self, responses: Iterable[AnalystResponse]) -> AnalystResponse:
        if not responses:
            raise RuntimeError("no analyst responses captured")
        return max(responses, key=lambda resp: resp.reliability)

    def _build_signal(
        self,
        *,
        primary: AnalystResponse,
        aggregation: AggregationResult,
        regime: str,
        symbol: str,
    ) -> Signal:
        side = primary.direction
        if side == "FLAT":
            side = "BUY" if aggregation.p_final >= 0.5 else "SELL"
        final_size = max(0.0, primary.size_hint_frac * primary.confidence)
        if side == "FLAT":
            final_size = 0.0
        metadata = {
            "weights": aggregation.weights,
            "uncertainty": aggregation.uncertainty,
            "tau": aggregation.tau_used,
            "regime": regime,
        }
        return Signal(
            symbol=symbol,
            side=side,
            strategy=primary.strategy,
            kelly_base=primary.size_hint_frac,
            safety_multiplier=1.0,
            final_size_frac=final_size,
            regime=regime,
            metadata=metadata,
        )

    async def _finalize_decision(
        self,
        *,
        responses: List[AnalystResponse],
        aggregation: AggregationResult | None,
        signal: Signal | None,
        approval: RiskGateApproval,
        execution: ExecutionPlan | None,
        snapshot: Dict[str, float],
        regime: str,
    ) -> FinalDecision:
        status: str = "approved" if approval.approved and execution else "rejected"
        GLOBAL_METRICS.record_decision(status == "approved")
        if status == "approved" and signal is not None:
            GLOBAL_METRICS.record_strategy_approval(signal.strategy)
        if not approval.approved:
            GLOBAL_METRICS.inc_metric("risk_blocked_total")
        snapshot_id = f"{snapshot['symbol']}:{snapshot.get('ts_utc', now_utc_iso())}"
        audit = AuditInfo(
            snapshot_id=snapshot_id,
            code_hash=self._code_hash,
            seed=self._seed,
            mode=self.config.mode,
            degradation_mode=aggregation.degradation_mode if aggregation else self._degradation.state.mode,
            kill_switch_state=self._kill_switch_state,
        )
        aggregation_payload = aggregation or AggregationResult(
            contributors=[],
            p_final=0.5,
            uncertainty=1.0,
            tau_used=self.config.llm.aggregator_tau,
            weights={},
            reliability_scores={},
            budget_spent_usd=0.0,
            budget_left_usd=self._budget_manager.base_budget,
            degradation_mode=self._degradation.state.mode,
            updated_at=now_utc_iso(),
        )
        signal_payload = signal or Signal(
            symbol=snapshot["symbol"],
            side="FLAT",
            strategy="POST_ONLY",
            kelly_base=0.0,
            safety_multiplier=1.0,
            final_size_frac=0.0,
            regime=regime,
        )
        decision = FinalDecision(
            status=status,
            reason=None if approval.approved else approval.reason,
            analyst=responses[-1] if responses else None,
            aggregation=aggregation_payload,
            signal=signal_payload,
            risk_gate=approval,
            execution=execution,
            audit=audit,
        )
        self._persist_decision(decision)
        if decision.status == "approved":
            await self.alert_sink.publish(self._format_alert(decision), level="info")
        self._health.last_snapshot_id = snapshot_id
        return decision

    def _persist_decision(self, decision: FinalDecision) -> None:
        payload = json.dumps(decision.model_dump(), ensure_ascii=False)
        with self.storage_paths.decisions.open("a", encoding="utf-8") as handle:
            handle.write(payload)
            handle.write("\n")
        if self._sqlite_conn:
            cursor = self._sqlite_conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO decisions(id, ts_utc, asset, status, side, size_frac, strategy, ttl_seconds, snapshot_id, code_hash, idempotency_key) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    decision.execution.idempotency_key if decision.execution else decision.audit.snapshot_id,
                    now_utc_iso(),
                    decision.signal.symbol,
                    decision.status,
                    decision.signal.side,
                    decision.signal.final_size_frac,
                    decision.signal.strategy,
                    decision.execution.legs[0].ttl_seconds if decision.execution else None,
                    decision.audit.snapshot_id,
                    decision.audit.code_hash,
                    decision.execution.idempotency_key if decision.execution else None,
                ),
            )
            self._sqlite_conn.commit()

    def _compose_market_snapshot(self, tick: Dict[str, Any]) -> Dict[str, float]:
        snapshot = build_market_window(tick, config=self.config)
        snapshot.setdefault("ts_utc", now_utc_iso())
        return snapshot

    def _format_alert(self, decision: FinalDecision) -> str:
        execution = decision.execution
        leg = execution.legs[0] if execution and execution.legs else None
        price_str = f"{leg.price:.2f}" if leg else "0"
        ttl_str = str(leg.ttl_seconds) if leg else "0"
        return (
            "[LLM Trading Arena • APPROVED]\n"
            f"Asset: {decision.signal.symbol}\n"
            f"Side: {decision.signal.side}\n"
            f"Size: {decision.signal.final_size_frac:.2%} ADV\n"
            f"Plan: {leg.strategy if leg else 'N/A'} @ {price_str} (TTL={ttl_str}s)\n"
            f"p_final={decision.aggregation.p_final:.2f}  U={decision.aggregation.uncertainty:.2f}  τ={decision.aggregation.tau_used:.2f}\n"
            f"mode={self.config.mode}  snapshot={decision.audit.snapshot_id}"
        )

    def _should_execute(self) -> bool:
        return self.mode in {TradingMode.CANARY, TradingMode.LIVE} and not self.dry_run

    def _enforce_time_sync(self) -> None:
        metrics = {}
        if hasattr(self.adapter, "metrics_snapshot"):
            try:
                metrics = self.adapter.metrics_snapshot() or {}
            except Exception:  # pragma: no cover - defensive
                metrics = {}
        skew = float(metrics.get("ts_offset_ms", 0.0) or 0.0)
        self._health.clock_skew_ms = skew
        max_skew = float(getattr(self.config.exchange, "max_clock_skew_ms", 0))
        if max_skew and abs(skew) > max_skew:
            self._health.breakers["time_sync"] = True
            raise RuntimeError("clock skew guard triggered")
        self._health.breakers.pop("time_sync", None)

    async def _handle_execution(self, decision: FinalDecision, snapshot: Dict[str, Any]) -> None:
        plan = decision.execution
        if not plan:
            return
        if self._should_execute():
            await self._submit_execution(plan, snapshot.get("symbol", ""))
            self._record_execution(decision=decision, fills=None, summary=None, simulated=False)
            return
        economics_cfg = self.config.economics.model_dump()
        fills, summary = simulate_order_execution(
            plan,
            snapshot,
            economics_cfg,
            decision_id=plan.idempotency_key,
        )
        self._record_execution(decision=decision, fills=fills, summary=summary, simulated=True)
        self._persist_fills(fills)

    async def _submit_execution(self, execution: ExecutionPlan, symbol: str) -> None:
        creds = self._load_creds()
        if not creds:
            return
        for leg in execution.legs:
            try:
                strategy = ExecutionStrategy(leg.strategy)
            except ValueError:
                continue
            try:
                side = OrderSide(leg.side)
            except ValueError:
                continue
            request = OrderRequest(
                symbol=leg.symbol,
                side=side,
                strategy=strategy,
                quantity=leg.quantity,
                price=leg.price,
                ttl_seconds=leg.ttl_seconds,
                client_order_id=execution.client_order_id,
            )
            await self.adapter.place_order(request, creds)

    def _load_creds(self) -> Optional[Any]:
        key = os.environ.get(self.config.exchange.api_key_env)
        secret = os.environ.get(self.config.exchange.api_secret_env)
        if not key or not secret:
            return None
        name = self.config.exchange.name.lower()
        if name == "bybit_unified":
            return BybitCreds(api_key=key, api_secret=secret)
        return BinanceCreds(api_key=key, api_secret=secret)

    def _record_execution(
        self,
        *,
        decision: FinalDecision,
        fills: Optional[List[SimulatedFill]],
        summary: Optional[Dict[str, Any]],
        simulated: bool,
    ) -> None:
        if not decision.execution:
            return
        record = {
            "decision_id": decision.execution.idempotency_key,
            "ts_utc": now_utc_iso(),
            "mode": self.config.mode,
            "simulated": simulated,
            "execution": decision.execution.model_dump(),
            "summary": summary,
            "fills": serialize_fills(fills or []),
        }
        with self.storage_paths.execution.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False))
            handle.write("\n")

    def _persist_fills(self, fills: List[SimulatedFill]) -> None:
        if not fills or not self._sqlite_conn:
            return
        records = serialize_fills(fills)
        cursor = self._sqlite_conn.cursor()
        cursor.executemany(
            "INSERT OR REPLACE INTO fills(id, decision_id, ts_utc, asset, price, qty, fee_usd, slippage_bps) VALUES(?,?,?,?,?,?,?,?)",
            [
                (
                    rec["id"],
                    rec["decision_id"],
                    rec["ts_utc"],
                    rec["asset"],
                    rec["price"],
                    rec["qty"],
                    rec.get("fee_usd"),
                    rec.get("slippage_bps"),
                )
                for rec in records
            ],
        )
        self._sqlite_conn.commit()


async def _async_main(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    validate_config(config)
    arena = TradingArena(config, dry_run=args.dry_run)
    await arena.initialize()
    try:
        await arena.run_once() if args.once else await arena.run_forever()
    finally:
        await arena.stop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LLM Trading Arena")
    parser.add_argument("--mode", choices=[m.value for m in TradingMode], required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--dry_run", action="store_true")
    parser.add_argument("--once", action="store_true", help="Run a single iteration and exit")
    return parser


def run_pipeline_cli(*, mode: str, config_path: str, dry_run: bool) -> None:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(["--mode", mode, "--config", config_path] + (["--dry_run"] if dry_run else []) + ["--once"])
    asyncio.run(_async_main(args))


def main() -> None:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args()
    asyncio.run(_async_main(args))


if __name__ == "__main__":
    main()
