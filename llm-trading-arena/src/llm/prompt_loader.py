from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Tuple

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


@lru_cache(maxsize=None)
def load_prompt(stage_name: str) -> Tuple[str, str]:
    """Return the shared system prompt and the stage-specific prompt text."""
    stage_key = stage_name.upper()
    system_path = PROMPTS_DIR / "system.md"
    stage_path = PROMPTS_DIR / f"analyst_{stage_key}.md"
    system_text = system_path.read_text(encoding="utf-8").strip()
    stage_text = stage_path.read_text(encoding="utf-8").strip()
    return system_text, stage_text


def clear_prompt_cache() -> None:
    """Invalidate the cached prompt contents (primarily used in tests)."""
    load_prompt.cache_clear()


__all__ = ["load_prompt", "clear_prompt_cache"]
