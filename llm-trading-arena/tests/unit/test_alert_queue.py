import time
from pathlib import Path

from src.alerts.queue import PersistentAlertQueue, QueuedAlert


def test_persistent_queue_backoff(tmp_path: Path) -> None:
    queue_path = tmp_path / "alerts.jsonl"
    queue = PersistentAlertQueue(queue_path)
    alert = QueuedAlert(message="hello", level="info", dedup_key="info:a", created_ts=time.time())
    queue.push(alert)
    assert queue.backlog == 1
    ready = list(queue.iter_ready(now=time.time()))
    assert ready[0].message == "hello"
    alert.backoff()
    queue.update(alert)
    ready_after_backoff = list(queue.iter_ready(now=time.time()))
    assert not ready_after_backoff  # not ready until delay passes
