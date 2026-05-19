from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "embedded" / "handoff_v8b2" / "manifests" / "V8B2_PACKAGE_MANIFEST.json"
DEFAULT_PACKAGE = REPO_ROOT / "embedded" / "handoff_v8b2"


@dataclass(frozen=True)
class CheckResult:
    level: str
    item: str
    message: str


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def check_required_paths(manifest: dict[str, Any], package_path: Path = DEFAULT_PACKAGE) -> list[CheckResult]:
    results: list[CheckResult] = []

    if not package_path.is_dir():
        return [CheckResult("FAIL", "package_path", f"Package directory not found: {package_path}")]

    for rel_dir in manifest.get("required_directories", []):
        path = package_path / rel_dir
        if path.is_dir():
            results.append(CheckResult("PASS", rel_dir, "Required directory present."))
        else:
            results.append(CheckResult("FAIL", rel_dir, "Required directory missing."))

    for rel_file in manifest.get("required_files", []):
        path = package_path / rel_file
        if path.is_file():
            results.append(CheckResult("PASS", rel_file, "Required file present."))
        else:
            results.append(CheckResult("FAIL", rel_file, "Required file missing."))

    return results


def check_manifest_semantics(manifest: dict[str, Any]) -> list[CheckResult]:
    results: list[CheckResult] = []

    expected_features = [
        "voltage_v",
        "temperature_c",
        "current_ma",
        "delta_voltage",
        "delta_temperature",
        "delta_current",
    ]
    feature_order = manifest.get("feature_order", [])
    if feature_order == expected_features:
        results.append(CheckResult("PASS", "feature_order", "Canonical feature order is exact."))
    else:
        results.append(CheckResult("FAIL", "feature_order", "Canonical feature order is missing or changed."))

    feature_units = manifest.get("feature_units", {})
    if feature_units.get("current_ma") == "mA":
        results.append(CheckResult("PASS", "current_ma_unit", "Current unit is mA."))
    else:
        results.append(CheckResult("FAIL", "current_ma_unit", "Current unit must be mA."))

    modes = set(manifest.get("validation_modes", []))
    expected_modes = {"GOLDEN", "EXTENDED", "ANOMALY"}
    if expected_modes.issubset(modes):
        results.append(CheckResult("PASS", "validation_modes", "GOLDEN, EXTENDED and ANOMALY are declared."))
    else:
        results.append(CheckResult("FAIL", "validation_modes", "Required validation modes are missing."))

    expected_status = manifest.get("expected_status", {})
    for mode in sorted(expected_modes):
        if expected_status.get(mode) == "PASS":
            results.append(CheckResult("PASS", f"expected_status.{mode}", f"{mode} expected status is PASS."))
        else:
            results.append(CheckResult("FAIL", f"expected_status.{mode}", f"{mode} expected status must be PASS."))

    claim_text = " ".join(manifest.get("claim_limits", [])).lower()
    required_claim_terms = ["field", "production", "physical sensor", "24/7", "soh"]
    missing_terms = [term for term in required_claim_terms if term not in claim_text]
    if missing_terms:
        results.append(CheckResult("FAIL", "claim_limits", f"Missing claim limit terms: {', '.join(missing_terms)}"))
    else:
        results.append(CheckResult("PASS", "claim_limits", "Claim limits cover field, production, sensor, 24/7 and SOH."))

    return results


def check_validator_paths(manifest: dict[str, Any], repo_root: Path = REPO_ROOT) -> list[CheckResult]:
    results: list[CheckResult] = []

    canonical = repo_root / manifest.get("canonical_validator", "")
    if canonical.is_file():
        results.append(CheckResult("PASS", "canonical_validator", f"Canonical validator present: {canonical.relative_to(repo_root)}"))
    else:
        results.append(CheckResult("FAIL", "canonical_validator", "Canonical validator is missing."))

    for rel_path in manifest.get("noncanonical_validator_paths", []):
        path = repo_root / rel_path
        if path.exists():
            results.append(CheckResult("WARN", rel_path, "Noncanonical validator duplicate exists. Prefer validation/validate_esp32_v8b2.py."))
        else:
            results.append(CheckResult("PASS", rel_path, "No noncanonical validator duplicate found."))

    return results


def run_checks(
    manifest_path: Path = DEFAULT_MANIFEST,
    package_path: Path = DEFAULT_PACKAGE,
    repo_root: Path = REPO_ROOT,
) -> tuple[str, list[CheckResult]]:
    manifest = load_manifest(manifest_path)
    results: list[CheckResult] = []
    results.extend(check_manifest_semantics(manifest))
    results.extend(check_required_paths(manifest, package_path))
    results.extend(check_validator_paths(manifest, repo_root))

    if any(result.level == "FAIL" for result in results):
        status = "FAIL"
    elif any(result.level == "WARN" for result in results):
        status = "WARN"
    else:
        status = "PASS"
    return status, results


def print_summary(status: str, results: list[CheckResult]) -> None:
    print(f"V8B2 package audit: {status}")
    for result in results:
        print(f"[{result.level}] {result.item}: {result.message}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit the public SOC-EDGE V8B2 replay package.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="Path to V8B2_PACKAGE_MANIFEST.json.")
    parser.add_argument("--package-path", type=Path, default=DEFAULT_PACKAGE, help="Path to embedded/handoff_v8b2.")
    args = parser.parse_args(argv)

    try:
        status, results = run_checks(args.manifest, args.package_path, REPO_ROOT)
    except Exception as exc:
        print(f"V8B2 package audit: FAIL")
        print(f"[FAIL] audit_exception: {exc}")
        return 1

    print_summary(status, results)
    return 1 if status == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
