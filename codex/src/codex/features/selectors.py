from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from ..config.models import FeatureFingerprintConfig
from ..contracts.features import DeterministicFeatures


OPTIONAL_FIELDS = {"sentiment_score", "event_severity"}


@dataclass
class FeatureSelector:
    fingerprint: FeatureFingerprintConfig

    def select(self, features: DeterministicFeatures) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        missing: list[str] = []
        for field in self.fingerprint.fields:
            if hasattr(features, field):
                payload[field] = getattr(features, field)
            elif field not in OPTIONAL_FIELDS:
                missing.append(field)
        if missing:
            raise KeyError(f"Missing deterministic features: {', '.join(missing)}")
        return payload


def project_features(features: DeterministicFeatures, fields: Iterable[str]) -> dict[str, Any]:
    selector = FeatureSelector(FeatureFingerprintConfig(fields=list(fields), deltas={}))
    return selector.select(features)
