import subprocess
import sys
from pathlib import Path


def test_pipeline_cli_runs_once(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    config = repo_root / "config.sample.yaml"
    cmd = [
        sys.executable,
        "-m",
        "src.app.production_pipeline",
        "--mode",
        "paper",
        "--config",
        str(config),
        "--dry_run",
        "--once",
    ]
    proc = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
