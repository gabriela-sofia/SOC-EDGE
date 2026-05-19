import json
from pathlib import Path


MANIFEST_PATH = Path("embedded/handoff_v8b2/manifests/V8B2_PACKAGE_MANIFEST.json")


def load_manifest():
    with MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_manifest_is_parseable():
    manifest = load_manifest()
    assert manifest["package_stage"] == "V8B2"


def test_feature_order_has_six_canonical_items():
    manifest = load_manifest()
    assert manifest["feature_order"] == [
        "voltage_v",
        "temperature_c",
        "current_ma",
        "delta_voltage",
        "delta_temperature",
        "delta_current",
    ]


def test_current_unit_is_ma():
    manifest = load_manifest()
    assert manifest["feature_units"]["current_ma"] == "mA"


def test_validation_modes_are_present():
    manifest = load_manifest()
    assert {"GOLDEN", "EXTENDED", "ANOMALY"}.issubset(set(manifest["validation_modes"]))


def test_claim_limits_cover_forbidden_claims():
    manifest = load_manifest()
    claim_limits = " ".join(manifest["claim_limits"]).lower()
    assert "field" in claim_limits
    assert "production" in claim_limits
    assert "physical sensor" in claim_limits
    assert "24/7" in claim_limits
    assert "soh" in claim_limits
