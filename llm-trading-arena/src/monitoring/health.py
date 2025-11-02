from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class HealthSnapshot:
    ready: bool
    schema_version: int
    last_snapshot_id: str
    mode: str
    venue: str
    kill_switch_state: str = "OFF"
    breakers: Dict[str, bool] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, object]:
        return {
            "ready": self.ready,
            "schema_version": self.schema_version,
            "last_snapshot_id": self.last_snapshot_id,
            "mode": self.mode,
            "venue": self.venue,
            "kill_switch_state": self.kill_switch_state,
            "breakers": self.breakers,
        }
