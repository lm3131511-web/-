from __future__ import annotations

import asyncio
import hashlib
import os
import time
from typing import Dict

from src.vendor import httpx

from .queue import PersistentAlertQueue, QueuedAlert

_LEVEL_ORDER = {"info": 0, "notice": 1, "warn": 2, "error": 3, "critical": 4}


class TelegramSink:
    def __init__(
        self,
        *,
        bot_token_env: str,
        chat_id_env: str,
        dedup_window_sec: int,
        min_level: str,
        queue: PersistentAlertQueue,
    ) -> None:
        self.bot_token_env = bot_token_env
        self.chat_id_env = chat_id_env
        self.dedup_window_sec = dedup_window_sec
        self.min_level = min_level.lower()
        self.queue = queue
        self._history: Dict[str, float] = {}
        self._lock = asyncio.Lock()
        self._dropped = 0

    async def publish(self, message: str, level: str) -> None:
        level = level.lower()
        if _LEVEL_ORDER.get(level, 0) < _LEVEL_ORDER.get(self.min_level, 0):
            return
        dedup_key = self._dedup_key(message, level)
        now = time.time()
        last_ts = self._history.get(dedup_key)
        if last_ts and now - last_ts < self.dedup_window_sec:
            return
        self._history[dedup_key] = now
        alert = QueuedAlert(message=message, level=level, dedup_key=dedup_key, created_ts=now)
        self.queue.push(alert)
        await self._flush_queue()

    async def _flush_queue(self) -> None:
        token = os.environ.get(self.bot_token_env)
        chat_id = os.environ.get(self.chat_id_env)
        if not token or not chat_id:
            return
        async with self._lock:
            async with httpx.AsyncClient(timeout=10) as client:
                for alert in list(self.queue.iter_ready()):
                    success = await self._send_one(client, token, chat_id, alert)
                    if success:
                        self.queue.mark_sent(alert)
                    else:
                        alert.backoff()
                        self.queue.update(alert)
                        self._dropped += 1
            self._report_queue_metrics()

    async def _send_one(self, client: httpx.AsyncClient, token: str, chat_id: str, alert: QueuedAlert) -> bool:
        payload = {"chat_id": chat_id, "text": alert.message}
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                return True
        except Exception:  # pragma: no cover - network failures
            pass
        return False

    def _report_queue_metrics(self) -> None:
        try:
            from ..monitoring.metrics import GLOBAL_METRICS

            GLOBAL_METRICS.update_alert_queue(self.queue.backlog, self._dropped)
        except Exception:  # pragma: no cover - defensive
            pass

    @staticmethod
    def _dedup_key(message: str, level: str) -> str:
        digest = hashlib.sha256(message.encode("utf-8")).hexdigest()[:16]
        return f"{level}:{digest}"
