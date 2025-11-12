from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from ..utils.logrotate import ensure_parent


@dataclass
class QueuedAlert:
    message: str
    level: str
    dedup_key: str
    created_ts: float
    attempts: int = 0
    next_attempt_ts: float = 0.0

    def backoff(self) -> None:
        self.attempts += 1
        delay = min(60, 2 ** min(self.attempts, 6))
        self.next_attempt_ts = time.time() + delay


class PersistentAlertQueue:
    def __init__(self, path: Path, *, max_bytes: int = 10 * 1024 * 1024, max_age_sec: int = 24 * 3600) -> None:
        self.path = path
        ensure_parent(path)
        self.max_bytes = max_bytes
        self.max_age_sec = max_age_sec
        self._queue: List[QueuedAlert] = []
        self._load_existing()

    def _load_existing(self) -> None:
        if not self.path.exists():
            return
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    raw = json.loads(line)
                    alert = QueuedAlert(
                        message=raw["message"],
                        level=raw["level"],
                        dedup_key=raw["dedup_key"],
                        created_ts=float(raw["created_ts"]),
                        attempts=int(raw.get("attempts", 0)),
                        next_attempt_ts=float(raw.get("next_attempt_ts", 0.0)),
                    )
                    self._queue.append(alert)
        except json.JSONDecodeError:
            self._queue.clear()
            self.path.unlink(missing_ok=True)

    @property
    def backlog(self) -> int:
        return len(self._queue)

    def push(self, alert: QueuedAlert) -> None:
        self._queue.append(alert)
        self._prune()
        self._persist()
        self.update_alert_metrics()

    def mark_sent(self, alert: QueuedAlert) -> None:
        if alert in self._queue:
            self._queue.remove(alert)
            self._persist()
            self.update_alert_metrics()

    def update(self, alert: QueuedAlert) -> None:
        # ensure alert order persists after updates
        if alert not in self._queue:
            self._queue.append(alert)
        self._persist()
        self.update_alert_metrics()

    def iter_ready(self, now: float | None = None) -> Iterable[QueuedAlert]:
        ref = time.time() if now is None else now
        return [item for item in list(self._queue) if item.next_attempt_ts <= ref]

    def _prune(self) -> None:
        # Drop alerts older than max_age_sec
        cutoff = time.time() - self.max_age_sec
        self._queue = [item for item in self._queue if item.created_ts >= cutoff]
        if self.path.exists() and self.path.stat().st_size > self.max_bytes:
            archive = self.path.with_suffix(self.path.suffix + f".{int(time.time())}.bak")
            self.path.replace(archive)
            self._persist()
        self.update_alert_metrics()

    def _persist(self) -> None:
        with self.path.open("w", encoding="utf-8") as handle:
            for item in self._queue:
                handle.write(
                    json.dumps(
                        {
                            "message": item.message,
                            "level": item.level,
                            "dedup_key": item.dedup_key,
                            "created_ts": item.created_ts,
                            "attempts": item.attempts,
                            "next_attempt_ts": item.next_attempt_ts,
                        }
                    )
                )
                handle.write("\n")

    def update_alert_metrics(self) -> None:
        try:
            from ..monitoring.metrics import GLOBAL_METRICS

            GLOBAL_METRICS.update_alert_queue(self.backlog, 0)
        except Exception:  # pragma: no cover - defensive
            pass
