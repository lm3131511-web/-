from __future__ import annotations

import abc
import asyncio
import json
from typing import Any, Dict, Tuple

from ...core.contracts.analyst import AnalystLLMOutput


class LLMProvider(abc.ABC):
    """Provide strict JSON completions for the Trading Arena prompts."""

    request_timeout: float = 8.0
    max_retries: int = 2
    backoff_seconds: float = 0.25

    def __init__(self, name: str) -> None:
        self.name = name
        self.mock_mode = False
        self.mode = "stub"
        self._last_meta: Dict[str, Any] = {
            "json_repair_used": False,
            "mock_fallback_used": False,
        }

    def set_mock_mode(self, value: bool) -> None:
        self.mock_mode = value

    def set_run_mode(self, mode: str) -> None:
        if mode not in {"stub", "real"}:
            raise ValueError(f"unsupported provider mode: {mode}")
        self.mode = mode

    @property
    def last_completion_meta(self) -> Dict[str, Any]:
        return dict(self._last_meta)

    async def complete_json(self, *, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        self._last_meta = {"json_repair_used": False, "mock_fallback_used": False}
        if self.mode != "real":
            payload = self._validate_payload(self._mock_completion(prompt=prompt, schema=schema))
            self._apply_usage_estimate(prompt, payload)
            return payload

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
                    self._ensure_usage(prompt, validated)
                    return validated
                except Exception as exc:
                    last_error = exc
            if attempt < attempts:
                await asyncio.sleep(self.backoff_seconds * attempt)

        if self.mock_mode:
            fallback = self._validate_payload(self._mock_completion(prompt=prompt, schema=schema))
            self._apply_usage_estimate(prompt, fallback)
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

    def _ensure_usage(self, prompt: str, payload: Dict[str, Any]) -> None:
        if "prompt_tokens" not in self._last_meta:
            self._apply_usage_estimate(prompt, payload)

    def _apply_usage_estimate(
        self,
        prompt: str,
        payload: Dict[str, Any],
        *,
        cost_usd: float | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
    ) -> None:
        prompt_tokens = prompt_tokens or max(1, len(prompt) // 4)
        completion_tokens = completion_tokens or max(
            1, len(json.dumps(payload, ensure_ascii=False)) // 4
        )
        if cost_usd is None:
            cost_usd = (prompt_tokens + completion_tokens) / 1000.0 * 0.002
        self._last_meta.update(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
        )

    def _extract_vars(self, prompt: str) -> Dict[str, Any]:
        marker = "VARIABLES:\n"
        if marker not in prompt:
            return {}
        section = prompt.split(marker, 1)[1]
        json_block = section.split("\n\nSTRICT_JSON_SCHEMA:", 1)[0]
        try:
            parsed = json.loads(json_block)
        except Exception:  # pragma: no cover - defensive
            return {}
        if not isinstance(parsed, dict):
            return {}
        merged: Dict[str, Any] = {}
        market_window = parsed.get("market_window")
        if isinstance(market_window, dict):
            merged.update(market_window)
        if "regime" in parsed:
            merged["regime"] = parsed["regime"]
        if "risk_level" in parsed:
            merged["risk_level"] = parsed["risk_level"]
        if "limits" in parsed:
            merged["limits"] = parsed["limits"]
        return merged
