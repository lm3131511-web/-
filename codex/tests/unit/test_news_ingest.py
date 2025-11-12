import time
from pathlib import Path

import asyncio

from codex.config.loader import load_settings
from codex.news_pipeline.ingest import NewsIngestor


def test_ingestor_writes_log(tmp_path):
    root = Path(__file__).resolve().parents[2]
    settings = load_settings(root / "configs" / "base.yaml")
    log_path = tmp_path / "news_ingest.jsonl"

    async def fake_twitter(_config):
        return [
            {
                "id": "1",
                "body": "Exchange paused withdrawals",
                "severity": "high",
                "sentiment": -0.9,
                "confidence": 0.9,
                "source": {"handle": "@CoinDesk", "followers": 80000},
                "timestamp": time.time(),
            }
        ]

    overrides = {"twitter": fake_twitter, "reddit": lambda _: [], "news": lambda _: []}
    ingestor = NewsIngestor(settings.news, log_path=log_path, overrides=overrides)
    record = asyncio.run(ingestor.poll_once())
    assert record is not None
    assert log_path.exists()
    contents = log_path.read_text(encoding="utf-8").strip()
    assert contents
    assert record.provider_counts["twitter"] == 1
