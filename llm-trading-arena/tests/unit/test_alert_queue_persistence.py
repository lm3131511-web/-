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


class _FailingResponse:
    status_code = 500


def test_queue_persists_on_network_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    queue_path = tmp_path / "alerts.jsonl"
    queue = PersistentAlertQueue(queue_path, max_bytes=256)
    sink = TelegramSink(
        bot_token_env="TELEGRAM_BOT_TOKEN",
        chat_id_env="TELEGRAM_CHAT_ID",
        dedup_window_sec=0,
        min_level="info",
        queue=queue,
    )
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")

    async def _failing_post(*args, **kwargs):  # type: ignore[unused-argument]
        await asyncio.sleep(0)
        return _FailingResponse()

    monkeypatch.setattr("src.vendor.httpx.AsyncClient.post", _failing_post)

    async def scenario() -> None:
        await sink.publish("critical failure", "error")
        await sink.publish("critical failure", "error")

    asyncio.run(scenario())

    assert queue.backlog >= 1
    assert queue_path.exists()
    snapshot = GLOBAL_METRICS.snapshot()
    assert snapshot["alert_queue_backlog"] == queue.backlog
    assert snapshot["alert_queue_dropped_total"] >= 1
