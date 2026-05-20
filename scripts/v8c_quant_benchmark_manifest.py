from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


FEATURE_ORDER = [
    "voltage_v",
    "temperature_c",
    "current_ma",
    "delta_voltage",
    "delta_temperature",
    "delta_current",
]

DEFAULT_OUTPUT_DIR = Path("reports/v8c_quant_benchmark")
DEFAULT_RELEVANT_FILES = [
    Path("embedded/handoff_v8b2/firmware/firmware_soc_v8b2_canonical.ino"),
    Path("embedded/handoff_v8b2/include/canonical_model_weights_v8b2.h"),
    Path("embedded/handoff_v8b2/include/replay_vectors_v8b2.h"),
    Path("embedded/handoff_v8b2/replay/canonical_golden_vectors_v8b2.csv"),
    Path("embedded/handoff_v8b2/replay/canonical_extended_replay_v8b2.csv"),
    Path("embedded/handoff_v8b2/anomaly/anomaly_replay_scenarios_v8b2.csv"),
    Path("embedded/quantization/V8B2_INT8_CANDIDATE_MANIFEST.json"),
    Path("embedded/quantization/canonical_model_weights_v8b2_int8_candidate.h"),
]


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, object]:
    return {
        "path": path.as_posix(),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() and path.is_file() else None,
        "sha256": sha256_file(path),
    }


def build_manifest(relevant_files: list[Path] | None = None) -> dict[str, object]:
    files = relevant_files or DEFAULT_RELEVANT_FILES
    return {
        "phase": "V8C_QUANT_BENCHMARK",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_model": {
            "name": "MLP V7C/V8B2 float",
            "architecture": "Input(6) -> Dense(64, ReLU) -> Dense(32, ReLU) -> Dense(1, linear)",
            "parameters": 2561,
            "target": "Method B / soc_q_cycle",
        },
        "experimental_candidate": {
            "status": "EXPERIMENTAL",
            "expected_role": "quantized_or_compact_candidate",
            "acceptance_requires": "same replay vectors, same feature order, same scaler policy, same clipping policy",
        },
        "feature_order": FEATURE_ORDER,
        "feature_units": {
            "voltage_v": "V",
            "temperature_c": "C",
            "current_ma": "mA",
            "delta_voltage": "V",
            "delta_temperature": "C",
            "delta_current": "mA",
        },
        "scaler_policy": "sklearn.MinMaxScaler-compatible; do not clip scaled features",
        "clipping_policy": "clip only final SOC to [0, 1]",
        "datasets_replay_used": [
            "embedded/handoff_v8b2/replay/canonical_golden_vectors_v8b2.csv",
            "embedded/handoff_v8b2/replay/canonical_extended_replay_v8b2.csv",
            "embedded/handoff_v8b2/anomaly/anomaly_replay_scenarios_v8b2.csv",
        ],
        "expected_metrics": [
            "GOLDEN replay status",
            "EXTENDED replay status",
            "ANOMALY no critical regression",
            "Python vs ESP32 parity",
            "mean latency",
            "p95 latency when enough samples exist",
            "free heap and minimum heap when available",
            "approximate flash or binary size when available",
            "MAE, RMSE, max_abs_diff against Python float baseline",
            "absence of NaN/inf",
            "final SOC clipped to [0, 1]",
        ],
        "claim_limits": [
            "experimental candidate only",
            "no field claim",
            "no production claim",
            "no physical sensor validation claim",
            "no 24/7 operation claim",
            "no operational SOH claim",
        ],
        "file_hashes": [file_record(path) for path in files],
    }


def write_json(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = data["file_hashes"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "exists", "size_bytes", "sha256"])
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate V8C quantization benchmark manifest.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--csv", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = build_manifest()
    json_path = args.json or args.output_dir / "v8c_quant_benchmark_manifest.json"
    csv_path = args.csv or args.output_dir / "v8c_quant_benchmark_file_hashes.csv"
    write_json(json_path, manifest)
    write_csv(csv_path, manifest)
    print(f"Manifest JSON: {json_path}")
    print(f"File hash CSV: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

