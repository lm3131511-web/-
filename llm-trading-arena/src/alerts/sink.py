from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .queue import PersistentAlertQueue
from .telegram import TelegramSink


class AlertSinkProtocol:
    async def publish(self, message: str, level: str) -> None: ...


def build_alert_sink(
    kind: str,
    monitoring_cfg: Dict[str, Any],
    telegram_cfg: Dict[str, str],
    queue_path: Path,
) -> AlertSinkProtocol:
    dedup = int(monitoring_cfg.get("alert_dedup_window_sec", 60))
    min_level = monitoring_cfg.get("alert_min_level", "info")
    queue = PersistentAlertQueue(queue_path)
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

        return WebhookSink(queue=queue, dedup_window_sec=dedup, min_level=min_level, monitoring_cfg=monitoring_cfg)
    raise ValueError(f"unsupported alert sink: {kind}")
