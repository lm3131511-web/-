from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Tuple

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


def _format_template(template: str, variables: Dict[str, str]) -> str:
    class _SafeDict(dict):
        def __missing__(self, key: str) -> str:  # pragma: no cover - defensive
            return "{" + key + "}"

    return template.format_map(_SafeDict(variables))


def build_compound_prompt(
    *,
    stage: str,
    provider: str,
    prompt_version: str,
    regime: str,
    variables_text: str,
    schema: Dict[str, Any],
) -> str:
    system_text, stage_text = load_prompt(stage)
    context = {
        "stage": stage,
        "provider": provider,
        "prompt_version": prompt_version,
        "regime": regime,
        "features_json": variables_text,
    }
    system_section = _format_template(system_text, context)
    stage_section = _format_template(stage_text, context)
    schema_block = json.dumps(schema, indent=2, sort_keys=True)
    return (
        f"{system_section}\n\n{stage_section}\n\nVARIABLES:\n{variables_text}\n\nSTRICT_JSON_SCHEMA:\n{schema_block}"
    )


__all__ = ["load_prompt", "clear_prompt_cache", "build_compound_prompt"]
