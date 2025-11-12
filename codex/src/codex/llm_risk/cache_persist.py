from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Any


@dataclass
class PersistedEntry:
    key: str
    value: dict[str, Any]
    expires_at: float


class SQLiteCachePersistor:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at REAL NOT NULL
                )
                """
            )
            conn.commit()

    def write(self, entry: PersistedEntry) -> None:
        with self._connect() as conn:
            conn.execute(
                "REPLACE INTO cache(key, value, expires_at) VALUES (?, ?, ?)",
                (entry.key, json.dumps(entry.value), entry.expires_at),
            )
            conn.commit()

    def read(self, key: str) -> Optional[PersistedEntry]:
        with self._connect() as conn:
            cur = conn.execute("SELECT value, expires_at FROM cache WHERE key=?", (key,))
            row = cur.fetchone()
        if not row:
            return None
        value, expires_at = row
        return PersistedEntry(key=key, value=json.loads(value), expires_at=expires_at)

    def prune_expired(self, now: float) -> int:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM cache WHERE expires_at < ?", (now,))
            conn.commit()
            return cur.rowcount
