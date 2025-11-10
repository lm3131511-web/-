from pathlib import Path

from src.utils.logrotate import rotate_daily, rotate_if_big


def test_rotate_if_big_moves_to_archive(tmp_path) -> None:
    log_path = tmp_path / "decisions.jsonl"
    log_path.write_text("x" * 10)
    rotate_if_big(log_path, max_bytes=5)
    archive_dir = log_path.parent / "archive"
    archived = list(archive_dir.glob("decisions.jsonl.*"))
    assert archived, "expected archived log file"


def test_rotate_daily_creates_copy(tmp_path) -> None:
    log_path = tmp_path / "execution.jsonl"
    log_path.write_text("line\n")
    rotate_daily(log_path)
    archive_dir = log_path.parent / "archive"
    archived = list(archive_dir.glob("execution.jsonl.*"))
    assert archived, "expected daily copy"
    for target in archived:
        assert target.read_text() == "line\n"
