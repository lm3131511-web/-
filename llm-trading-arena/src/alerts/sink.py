from __future__ import annotations

from typing import Any, Dict

from .telegram import TelegramSink


class AlertSinkProtocol:
    async def publish(self, message: str, level: str) -> None: ...


def build_alert_sink(
    kind: str,
    monitoring_cfg: Dict[str, Any],
    telegram_cfg: Dict[str, str],
) -> AlertSinkProtocol:
    if kind != "telegram":
        raise ValueError(f"unsupported alert sink: {kind}")
    return TelegramSink(
        bot_token_env=telegram_cfg.get("bot_token_env", "TELEGRAM_BOT_TOKEN"),
        chat_id_env=telegram_cfg.get("chat_id_env", "TELEGRAM_CHAT_ID"),
        dedup_window_sec=int(monitoring_cfg.get("alert_dedup_window_sec", 60)),
    )
