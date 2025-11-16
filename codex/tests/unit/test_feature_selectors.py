import pytest

from codex.config.models import FeatureFingerprintConfig
from codex.contracts.features import DeterministicFeatures
from codex.features.selectors import FeatureSelector, project_features


def test_selector_extracts_required_fields():
    selector = FeatureSelector(
        FeatureFingerprintConfig(fields=["regime", "rsi_14", "atr_pct"], deltas={})
    )
    features = DeterministicFeatures(
        regime="bull",
        rsi_14=55.0,
        atr_pct=0.4,
        spread_bps=3.0,
    )
    payload = selector.select(features)
    assert payload == {"regime": "bull", "rsi_14": 55.0, "atr_pct": 0.4}


def test_selector_raises_for_missing_fields():
    selector = FeatureSelector(FeatureFingerprintConfig(fields=["missing"], deltas={}))
    features = DeterministicFeatures(regime="base", rsi_14=50.0, atr_pct=0.3, spread_bps=2.0)
    with pytest.raises(KeyError):
        selector.select(features)


def test_project_features_helper():
    features = DeterministicFeatures(regime="sideways", rsi_14=49.0, atr_pct=0.2, spread_bps=1.5)
    projected = project_features(features, ["regime", "spread_bps"])
    assert projected == {"regime": "sideways", "spread_bps": 1.5}
