from __future__ import annotations

import abc
import asyncio
import json
from typing import Any, Dict, Tuple

from src.vendor import yaml

from ...core.contracts.analyst import AnalystLLMOutput


class LLMProvider(abc.ABC):
    """Provide strict JSON completions for the Trading Arena prompts."""

    request_timeout: float = 8.0
    max_retries: int = 2
    backoff_seconds: float = 0.25

    def __init__(self, name: str) -> None:
        self.name = name
        self.mock_mode = False
        self._last_meta: Dict[str, Any] = {
            "json_repair_used": False,
            "mock_fallback_used": False,
        }

    def set_mock_mode(self, value: bool) -> None:
        self.mock_mode = value

    @property
    def last_completion_meta(self) -> Dict[str, Any]:
        return dict(self._last_meta)

    async def complete_json(self, *, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        self._last_meta = {"json_repair_used": False, "mock_fallback_used": False}
        last_error: Exception | None = None
        attempts = self.max_retries if not self.mock_mode else 1
        for attempt in range(1, attempts + 1):
            try:
                raw = await asyncio.wait_for(
                    self._raw_complete(prompt=prompt, schema=schema),
                    timeout=self.request_timeout,
                )
            except Exception as exc:  # pragma: no cover - network paths
                last_error = exc
            else:
                try:
                    payload, repaired = self._coerce_json(raw)
                    validated = self._validate_payload(payload)
                    if repaired:
                        self._last_meta["json_repair_used"] = True
                    return validated
                except Exception as exc:
                    last_error = exc
            if attempt < attempts:
                await asyncio.sleep(self.backoff_seconds * attempt)

        if self.mock_mode:
            fallback = self._validate_payload(self._mock_completion(prompt=prompt, schema=schema))
            self._last_meta.update(json_repair_used=True, mock_fallback_used=True)
            return fallback
        raise RuntimeError(f"{self.name} provider failed") from last_error

    @abc.abstractmethod
    async def _raw_complete(self, *, prompt: str, schema: Dict[str, Any]) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def _mock_completion(self, *, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def _coerce_json(self, raw: str) -> Tuple[Dict[str, Any], bool]:
        candidate = raw.strip()
        repaired = False
        if not candidate:
            raise ValueError("empty completion")
        if not candidate.lstrip().startswith("{"):
            start = candidate.find("{")
            end = candidate.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise ValueError("completion missing JSON object")
            candidate = candidate[start : end + 1]
            repaired = True
        data = json.loads(candidate)
        if not isinstance(data, dict):
            raise ValueError("completion must be a JSON object")
        return data, repaired

    def _validate_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        model = AnalystLLMOutput.model_validate(payload)
        return model.model_dump()

    def _extract_vars(self, prompt: str) -> Dict[str, Any]:
        marker = "VARS:\n"
        if marker not in prompt:
            return {}
        section = prompt.split(marker, 1)[1]
        yaml_block = section.split("\n---", 1)[0]
        try:
            parsed = yaml.safe_load(yaml_block) or {}
            if isinstance(parsed, dict):
                return parsed
        except Exception:  # pragma: no cover - defensive
            return {}
        return {}
