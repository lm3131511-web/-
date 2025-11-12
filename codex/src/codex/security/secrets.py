from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SecretValue:
    value: str
    ttl_seconds: int


class SecretVault:
    def __init__(self, provider: Any | None = None) -> None:
        self.provider = provider

    def fetch(self, key: str) -> SecretValue:
        # In production this would hit Vault/SOPS. Here we simply raise to signal the value is missing.
        raise RuntimeError(f"Secret {key} must be supplied via secure storage")
