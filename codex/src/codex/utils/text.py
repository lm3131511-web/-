from __future__ import annotations

import re
from typing import Iterable

URL_RE = re.compile(r"https?://\S+")
MENTION_RE = re.compile(r"@[\w_]+")
WHITESPACE_RE = re.compile(r"\s+")


def strip_urls(text: str) -> str:
    return URL_RE.sub("", text)


def strip_mentions(text: str) -> str:
    return MENTION_RE.sub("", text)


def normalize_whitespace(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text).strip()


def sanitize_text(text: str, *, remove_urls: bool, remove_mentions: bool, max_chars: int) -> str:
    cleaned = text
    if remove_urls:
        cleaned = strip_urls(cleaned)
    if remove_mentions:
        cleaned = strip_mentions(cleaned)
    cleaned = normalize_whitespace(cleaned)
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars]
    return cleaned


def ensure_trusted_sources(sources: Iterable[dict], *, whitelist: set[str], min_followers: int) -> list[dict]:
    filtered: list[dict] = []
    for src in sources:
        handle = str(src.get("handle", "")).lower()
        followers = int(src.get("followers", 0))
        if whitelist and handle not in {w.lower() for w in whitelist}:
            continue
        if followers < min_followers:
            continue
        filtered.append(src)
    return filtered
