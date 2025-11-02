from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from ..core.contracts import RiskGateApproval


@dataclass
class CooldownState:
    last_trade_ts: float = 0.0
    stop_ts: float = 0.0


@dataclass
class RiskLimits:
    per_trade_loss_pct: float
    per_day_loss_pct: float
    max_drawdown_pct: float


@dataclass
class MarketLimits:
    max_spread_bps: float


@dataclass
class PnLBreakers:
    day_loss_pct: float
    week_loss_pct: float


@dataclass
class CooldownConfig:
    after_stop_sec: float
    min_between_trades_sec: float


@dataclass
class CircuitBreakers:
    ece_threshold: float
    hitrate_drop_window: int


@dataclass
class RiskConfig:
    limits: RiskLimits
    market: MarketLimits
    pnl_breaker: PnLBreakers
    cooldowns: CooldownConfig
    circuit_breakers: CircuitBreakers


@dataclass
class RiskState:
    cooldown: CooldownState = field(default_factory=CooldownState)
    circuit_tripped: bool = False
    pnl_tripped: bool = False


class RiskGate:
    def __init__(self, config: RiskConfig, sell_enabled: bool) -> None:
        self.config = config
        self.sell_enabled = sell_enabled
        self.state = RiskState()

    def approve(self, *, spread_bps: float, is_buy: bool, losses_pct: float) -> RiskGateApproval:
        now = time.time()
        cooldown_active = False
        if now - self.state.cooldown.last_trade_ts < self.config.cooldowns.min_between_trades_sec:
            cooldown_active = True
        if now < self.state.cooldown.stop_ts:
            cooldown_active = True

        reason = None
        approved = True
        if cooldown_active:
            approved = False
            reason = "cooldown"
        elif not is_buy and not self.sell_enabled:
            approved = False
            reason = "sell_disabled"
        elif spread_bps > self.config.market.max_spread_bps:
            approved = False
            reason = "spread_too_wide"
        elif losses_pct > self.config.limits.per_trade_loss_pct:
            approved = False
            reason = "loss_limit"
        if losses_pct > self.config.pnl_breaker.day_loss_pct:
            self.state.pnl_tripped = True
            approved = False
            reason = "pnl_breaker"
        if self.state.pnl_tripped:
            approved = False
            reason = reason or "pnl_breaker"

        if self.state.circuit_tripped:
            approved = False
            reason = reason or "circuit_breaker"

        approval = RiskGateApproval(
            approved=approved,
            reason=reason,
            limit_check={"spread_bps": spread_bps, "losses_pct": losses_pct},
            cooldown_active=cooldown_active,
            circuit_breaker_tripped=self.state.circuit_tripped,
            pnl_breaker_tripped=self.state.pnl_tripped,
        )

        # При одобренной сделке фиксируем "последнюю" активность – для min_between_trades
        if approval.approved:
            self.state.cooldown.last_trade_ts = now

        # Если сработали запрет/брейкеры — выставим стоп-кулдаун
        if reason in {"loss_limit", "pnl_breaker"}:
            self.state.cooldown.stop_ts = now + self.config.cooldowns.after_stop_sec

        return approval

    def stop_trading(self, seconds: float) -> None:
        self.state.cooldown.stop_ts = time.time() + seconds

    def trip_circuit_breaker(self) -> None:
        self.state.circuit_tripped = True

    def reset(self) -> None:
        self.state = RiskState()
