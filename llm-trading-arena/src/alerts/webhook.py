from __future__ import annotations

import asyncio
import hashlib
import os
import time
from typing import Dict

from src.vendor import httpx

from .queue import PersistentAlertQueue, QueuedAlert


class WebhookSink:
    def __init__(
        self,
        *,
        queue: PersistentAlertQueue,
        dedup_window_sec: int,
        min_level: str,
        monitoring_cfg: Dict[str, object],
    ) -> None:
        self.queue = queue
        self.dedup_window_sec = dedup_window_sec
        self.min_level = min_level.lower()
        self.monitoring_cfg = monitoring_cfg
        self._history: Dict[str, float] = {}
        self._lock = asyncio.Lock()
        self._dropped = 0

    async def publish(self, message: str, level: str) -> None:
        level = level.lower()
        if self._level_rank(level) < self._level_rank(self.min_level):
            return
        dedup_key = self._dedup_key(message, level)
        now = time.time()
        if self._history.get(dedup_key, 0) + self.dedup_window_sec > now:
            return
        self._history[dedup_key] = now
        alert = QueuedAlert(message=message, level=level, dedup_key=dedup_key, created_ts=now)
        self.queue.push(alert)
        await self._flush()

    async def _flush(self) -> None:
        env_key = str(self.monitoring_cfg.get("webhook_env", "ALERT_WEBHOOK_URL"))
        url = os.environ.get(env_key)
        if not url:
            return
        async with self._lock:
            async with httpx.AsyncClient(timeout=10) as client:
                for alert in list(self.queue.iter_ready()):
                    try:
                        response = await client.post(url, json={"message": alert.message, "level": alert.level})
                        if response.status_code == 200:
                            self.queue.mark_sent(alert)
                            continue
                    except Exception:  # pragma: no cover
                        pass
                    alert.backoff()
                    self.queue.update(alert)
                    self._dropped += 1
            self._report_queue_metrics()

    def _report_queue_metrics(self) -> None:
        try:
            from ..monitoring.metrics import GLOBAL_METRICS

            GLOBAL_METRICS.update_alert_queue(self.queue.backlog, self._dropped)
        except Exception:  # pragma: no cover
            pass

    @staticmethod
    def _dedup_key(message: str, level: str) -> str:
        digest = hashlib.sha256(message.encode("utf-8")).hexdigest()[:16]
        return f"{level}:{digest}"

    @staticmethod
    def _level_rank(level: str) -> int:
        order = {"info": 0, "notice": 1, "warn": 2, "error": 3, "critical": 4}
        return order.get(level, 0)
