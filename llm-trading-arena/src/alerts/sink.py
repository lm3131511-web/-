from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .queue import PersistentAlertQueue
from .telegram import TelegramSink


class AlertSinkProtocol:
    async def publish(self, message: str, level: str) -> None: ...


def build_alert_sink(
    kind: str,
    alerts_cfg: Dict[str, Any],
    telegram_cfg: Dict[str, str],
    queue_path: Path,
) -> AlertSinkProtocol:
    dedup = int(alerts_cfg.get("dedup_window_sec", 60))
    min_level = alerts_cfg.get("min_level", "info")
    queue = PersistentAlertQueue(queue_path)
    if kind == "none":
        return _NullAlertSink(queue=queue)
    if kind == "telegram":
        return TelegramSink(
            bot_token_env=telegram_cfg.get("bot_token_env", "TELEGRAM_BOT_TOKEN"),
            chat_id_env=telegram_cfg.get("chat_id_env", "TELEGRAM_CHAT_ID"),
            dedup_window_sec=dedup,
            min_level=min_level,
            queue=queue,
        )
    if kind == "webhook":
        from .webhook import WebhookSink

        return WebhookSink(queue=queue, dedup_window_sec=dedup, min_level=min_level, monitoring_cfg=alerts_cfg)
    raise ValueError(f"unsupported alert sink: {kind}")


class _NullAlertSink(AlertSinkProtocol):
    def __init__(self, *, queue: PersistentAlertQueue) -> None:
        self.queue = queue

    async def publish(self, message: str, level: str) -> None:  # pragma: no cover - trivial noop
        self.queue.update_alert_metrics()
