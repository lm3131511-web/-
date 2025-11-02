from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from typing import Dict, Tuple

from src.vendor import httpx


@dataclass
class _DedupEntry:
    message: str
    ts: float


class TelegramSink:
    def __init__(self, bot_token_env: str, chat_id_env: str, dedup_window_sec: int) -> None:
        self.bot_token_env = bot_token_env
        self.chat_id_env = chat_id_env
        self.dedup_window_sec = dedup_window_sec
        self._history: Dict[str, _DedupEntry] = {}
        self._lock = asyncio.Lock()

    async def publish(self, message: str, level: str) -> None:
        async with self._lock:
            key = f"{level}:{message}"
            now = time.time()
            entry = self._history.get(key)
            if entry and now - entry.ts < self.dedup_window_sec:
                return
            self._history[key] = _DedupEntry(message=message, ts=now)
        token = os.environ.get(self.bot_token_env)
        chat_id = os.environ.get(self.chat_id_env)
        if not token or not chat_id:
            return
        async with httpx.AsyncClient(timeout=10) as client:
            payload = {"chat_id": chat_id, "text": message}
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            await client.post(url, json=payload)
