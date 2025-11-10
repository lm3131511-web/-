import time

from src.alerts.queue import PersistentAlertQueue, QueuedAlert


def test_alert_queue_rotates_when_large(tmp_path) -> None:
    queue_path = tmp_path / "alerts.jsonl"
    queue = PersistentAlertQueue(queue_path, max_bytes=10, max_age_sec=1)
    for i in range(5):
        queue.push(QueuedAlert(message=f"msg-{i}", level="info", dedup_key=str(i), created_ts=time.time()))
    backups = list(tmp_path.glob("alerts.jsonl.*.bak"))
    assert backups, "expected backup file after rotation"
