from datetime import datetime

from src.utils.time import now_utc_iso


def test_now_utc_iso_format() -> None:
    ts = now_utc_iso()
    assert ts.endswith("Z")
    # ensure ISO-8601 compatibility
    parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
