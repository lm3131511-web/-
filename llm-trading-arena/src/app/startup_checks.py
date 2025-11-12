from __future__ import annotations

from pathlib import Path

from ..core.contracts import generate_json_schemas


SCHEMA_DIR = Path(__file__).resolve().parents[1] / "core" / "schemas_json"


def ensure_contract_schemas() -> None:
    generate_json_schemas(SCHEMA_DIR)
