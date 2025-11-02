import subprocess
import sys
from pathlib import Path


def test_run_paper():
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.app.production_pipeline",
            "--mode",
            "paper",
            "--config",
            "config.sample.yaml",
            "--dry_run",
        ],
        cwd=str(Path(__file__).resolve().parent.parent),
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
