from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class HealthSnapshot:
    ready: bool
    schema_version: int
    last_snapshot_id: str
    mode: str
    venue: str

    def as_dict(self) -> Dict[str, str | bool | int]:
        return {
            "ready": self.ready,
            "schema_version": self.schema_version,
            "last_snapshot_id": self.last_snapshot_id,
            "mode": self.mode,
            "venue": self.venue,
        }
