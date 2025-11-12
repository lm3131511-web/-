from __future__ import annotations

import threading
from typing import Any, Dict


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._metrics: Dict[str, Any] = self._default_metrics()

    def _default_metrics(self) -> Dict[str, Any]:
        return {
            "schema_version": 1,
            "decisions_total": 0,
            "approved_ratio": 0.0,
            "risk_blocked_total": 0,
            "ece": {200: 0.0, 500: 0.0, 1000: 0.0},
            "brier": {200: 0.0, 500: 0.0, 1000: 0.0},
            "spearman": {200: 0.0, 500: 0.0, 1000: 0.0},
            "venue_latency_ms_avg": 0.0,
            "venue_latency_ms_p99": 0.0,
            "order_reject_rate": 0.0,
            "order_rejects_total": 0,
            "rate_limit_hits": 0,
            "ws_reconnects_total": 0,
            "precision_cache_invalidations_total": 0,
            "schema_guard_hits_total": 0,
            "cold_start_seconds": 0.0,
            "kill_switch_state": "OFF",
            "llm_cost_per_min": 0.0,
            "llm_cost_per_min_A": 0.0,
            "llm_cost_per_min_B": 0.0,
            "llm_cost_per_min_C": 0.0,
            "llm_cost_breakdown": {},
            "llm_token_usage_per_provider": {},
            "degradation_mode": "full",
            "u_score": 0.0,
            "alert_queue_backlog": 0,
            "alert_queue_dropped_total": 0,
            "prompt_versions": {},
            "prompt_hashes": {},
            "weights_used": {},
            "approved_by_strategy": {
                "POST_ONLY": 0,
                "IOC": 0,
                "POV": 0,
                "TWAP": 0,
            },
            "llm_json_repair_rate": 0.0,
            "llm_completion_total": 0,
            "llm_json_repairs_total": 0,
            "budget_sentry_hits": 0,
            "adv_table_stale": False,
        }

    def set_metric(self, name: str, value: Any) -> None:
        with self._lock:
            self._metrics[name] = value

    def inc_metric(self, name: str, value: float = 1.0) -> None:
        with self._lock:
            self._metrics[name] = self._metrics.get(name, 0.0) + value

    def record_decision(self, approved: bool) -> None:
        with self._lock:
            total = self._metrics.get("decisions_total", 0) + 1
            approved_total = self._metrics.get("approved_total", 0) + (1 if approved else 0)
            self._metrics["decisions_total"] = total
            self._metrics["approved_total"] = approved_total
            self._metrics["approved_ratio"] = approved_total / total

    def update_alert_queue(self, backlog: int, dropped: int) -> None:
        with self._lock:
            self._metrics["alert_queue_backlog"] = backlog
            self._metrics["alert_queue_dropped_total"] = dropped

    def set_degradation(self, mode: str, u_score: float) -> None:
        with self._lock:
            self._metrics["degradation_mode"] = mode
            self._metrics["u_score"] = u_score

    def record_prompt(self, stage: str, version: str, prompt_hash: str) -> None:
        with self._lock:
            versions = dict(self._metrics.get("prompt_versions", {}))
            versions[stage] = version
            hashes = dict(self._metrics.get("prompt_hashes", {}))
            hashes[stage] = prompt_hash
            self._metrics["prompt_versions"] = versions
            self._metrics["prompt_hashes"] = hashes

    def record_llm_completion(self, *, repaired: bool) -> None:
        with self._lock:
            total = self._metrics.get("llm_completion_total", 0) + 1
            repairs = self._metrics.get("llm_json_repairs_total", 0) + (1 if repaired else 0)
            self._metrics["llm_completion_total"] = total
            self._metrics["llm_json_repairs_total"] = repairs
            self._metrics["llm_json_repair_rate"] = repairs / total if total else 0.0

    def record_llm_usage(
        self,
        *,
        stage: str,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
    ) -> None:
        with self._lock:
            usage = dict(self._metrics.get("llm_token_usage_per_provider", {}))
            usage[provider] = usage.get(provider, 0) + prompt_tokens + completion_tokens
            self._metrics["llm_token_usage_per_provider"] = usage

            breakdown = dict(self._metrics.get("llm_cost_breakdown", {}))
            breakdown[stage] = float(cost_usd)
            self._metrics["llm_cost_breakdown"] = breakdown
            self._metrics[f"llm_cost_per_min_{stage}"] = float(cost_usd)
            self._metrics["llm_cost_per_min"] = sum(breakdown.values())

    def record_weights(self, weights: Dict[str, float]) -> None:
        with self._lock:
            current = dict(self._metrics.get("weights_used", {}))
            for stage, weight in weights.items():
                current[stage] = float(weight)
            self._metrics["weights_used"] = current

    def record_strategy_approval(self, strategy: str) -> None:
        with self._lock:
            approvals = dict(self._metrics.get("approved_by_strategy", {}))
            approvals[strategy] = approvals.get(strategy, 0) + 1
            self._metrics["approved_by_strategy"] = approvals

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._metrics)

    def reset(self) -> None:
        with self._lock:
            self._metrics = self._default_metrics()


GLOBAL_METRICS = MetricsRegistry()
