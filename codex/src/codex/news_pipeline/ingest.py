from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import Any, List, Mapping, MutableMapping

from ..config.loader import load_settings
from ..config.models import NewsConfig, ProviderConfig, Settings
from ..contracts.sentiment import SentimentEvent
from ..monitoring.metrics import news_events_counter
from ..persistence.models import NewsIngestRecord
from ..persistence.store import NewsLog
from .aggregate import aggregate_sentiment
from .providers import NewsProvider, RedditProvider, TwitterProvider
from .providers.base import FetchCallable
from .sanitize import sanitize_items

DEFAULT_LOG_PATH = Path("data/logs/news_ingest.jsonl")


class NewsIngestor:
    def __init__(
        self,
        config: NewsConfig,
        *,
        log_path: Path | None = None,
        overrides: Mapping[str, FetchCallable] | None = None,
    ) -> None:
        self.config = config
        self.log = NewsLog(str((log_path or DEFAULT_LOG_PATH).resolve()))
        self.overrides = dict(overrides or {})
        self._providers = self._build_providers()

    def _build_providers(self) -> List[tuple[str, ProviderConfig, object]]:
        providers: List[tuple[str, ProviderConfig, object]] = []
        cfg = self.config.providers
        if "twitter" in cfg:
            providers.append(("twitter", cfg["twitter"], TwitterProvider(cfg["twitter"], self.overrides.get("twitter"))))
        if "reddit" in cfg:
            providers.append(("reddit", cfg["reddit"], RedditProvider(cfg["reddit"], self.overrides.get("reddit"))))
        if "news" in cfg:
            providers.append(("news", cfg["news"], NewsProvider(cfg["news"], self.overrides.get("news"))))
        return providers

    async def poll_once(self) -> NewsIngestRecord | None:
        aggregated_items: List[dict[str, Any]] = []
        provider_counts: MutableMapping[str, int] = {}
        sanitizer = self.config.sanitizer
        for name, provider_config, provider in self._providers:
            if not provider_config.enabled:
                continue
            raw_items = await provider.fetch()  # type: ignore[call-arg]
            if not raw_items:
                continue
            provider_counts[name] = len(raw_items)
            sanitized = sanitize_items(raw_items, sanitizer)
            aggregated_items.extend(sanitized)
        if not aggregated_items:
            return None
        events = [self._to_event(item) for item in aggregated_items]
        aggregated = aggregate_sentiment(events, self.config.aggregation)
        for event in events:
            news_events_counter.labels(severity=event.severity).inc()
        record = NewsIngestRecord(
            aggregated=aggregated,
            provider_counts=dict(provider_counts),
            items=aggregated_items,
        )
        self.log.write_event(record)
        return record

    @staticmethod
    def _to_event(item: Mapping[str, Any]) -> SentimentEvent:
        severity = str(item.get("severity", "none"))
        sentiment = float(item.get("sentiment", 0.0))
        sentiment = max(-1.0, min(1.0, sentiment))
        confidence = float(item.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))
        trusted = bool(item.get("trusted") or item.get("source", {}).get("trusted"))
        source = str(item.get("provider") or item.get("source", {}).get("handle") or "news")
        return SentimentEvent(
            source=source,
            severity=severity,
            sentiment=sentiment,
            confidence=confidence,
            trusted=trusted,
        )


async def run_ingest(config: NewsConfig, *, interval_sec: int, overrides: Mapping[str, FetchCallable] | None = None) -> None:
    ingestor = NewsIngestor(config, overrides=overrides)
    while True:
        await ingestor.poll_once()
        await asyncio.sleep(interval_sec)


def load_settings_for_env(env: str) -> Settings:
    root = Path(__file__).resolve().parents[3]
    base_path = root / "configs" / "base.yaml"
    overlay_path = root / "configs" / f"{env}.yaml"
    overlay = overlay_path if overlay_path.exists() else None
    return load_settings(base_path, overlay)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Codex news ingest pipeline")
    parser.add_argument("--env", default="dev", help="Configuration environment to use")
    parser.add_argument("--interval", type=int, default=60, help="Polling interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run a single ingest iteration and exit")
    return parser.parse_args()


async def main_async(args: argparse.Namespace | None = None) -> None:
    args = args or parse_args()
    settings = load_settings_for_env(args.env)
    config = settings.news
    ingestor = NewsIngestor(config)
    if args.once:
        await ingestor.poll_once()
        return
    while True:
        await ingestor.poll_once()
        await asyncio.sleep(args.interval)


def main() -> None:
    args = parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":  # pragma: no cover - CLI guard
    main()
