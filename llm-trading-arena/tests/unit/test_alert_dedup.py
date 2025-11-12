import asyncio
from pathlib import Path

import pytest

from src.alerts.queue import PersistentAlertQueue
from src.alerts.telegram import TelegramSink
from src.monitoring.metrics import GLOBAL_METRICS


@pytest.fixture(autouse=True)
def _reset_metrics() -> None:
    GLOBAL_METRICS.reset()
    yield
    GLOBAL_METRICS.reset()


def test_alert_dedup_window(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    queue_path = tmp_path / "alerts.jsonl"
    queue = PersistentAlertQueue(queue_path)
    sink = TelegramSink(
        bot_token_env="TELEGRAM_BOT_TOKEN",
        chat_id_env="TELEGRAM_CHAT_ID",
        dedup_window_sec=30,
        min_level="info",
        queue=queue,
    )
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    async def scenario() -> None:
        await sink.publish("message", "info")
        await sink.publish("message", "info")
        assert queue.backlog == 1
        sink._history.clear()
        await sink.publish("message", "info")

    asyncio.run(scenario())
    assert queue.backlog == 2
