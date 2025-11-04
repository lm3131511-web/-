from __future__ import annotations

from pathlib import Path

from src.app.startup_checks import SCHEMA_DIR, ensure_contract_schemas


def test_schema_files_exist() -> None:
    ensure_contract_schemas()
    files = list(Path(SCHEMA_DIR).glob("*.json"))
    assert any(f.name == "FinalDecision.json" for f in files)
    version_file = Path(SCHEMA_DIR) / "__version__.py"
    assert version_file.exists()
