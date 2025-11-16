from __future__ import annotations

from typing import Iterable

from ..config.models import SanitizerConfig
from ..utils.text import sanitize_text, ensure_trusted_sources


def sanitize_items(items: Iterable[dict], config: SanitizerConfig) -> list[dict]:
    sanitized: list[dict] = []
    for item in items:
        body = str(item.get("body", ""))
        cleaned = sanitize_text(
            body,
            remove_urls=config.strip_urls,
            remove_mentions=config.strip_mentions,
            max_chars=config.max_chars,
        )
        sanitized.append({**item, "body": cleaned})
    return sanitized


def filter_trusted(items: Iterable[dict], *, whitelist: set[str], min_followers: int) -> list[dict]:
    trusted_sources = ensure_trusted_sources(
        (item.get("source", {}) for item in items),
        whitelist=whitelist,
        min_followers=min_followers,
    )
    trusted_handles = {src["handle"].lower() for src in trusted_sources}
    return [item for item in items if str(item.get("source", {}).get("handle", "")).lower() in trusted_handles]
