from __future__ import annotations

import argparse
import csv
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
DEFAULT_TEMPLATE = Path("embedded/handoff_v8c_quant_benchmark/reports/template_esp32_quant_benchmark_return.csv")
REPLAY_FILES = [
    "embedded/handoff_v8b2/replay/canonical_golden_vectors_v8b2.csv",
    "embedded/handoff_v8b2/replay/canonical_extended_replay_v8b2.csv",
    "embedded/handoff_v8b2/anomaly/anomaly_replay_scenarios_v8b2.csv",
]
LOG_FIELDS = [
    "sample_id",
    "mode",
    "model_variant",
    "soc_final",
    "inference_time_ms",
    "free_heap",
    "min_free_heap",
    "flash_bytes",
    "anomaly_flag",
    "status",
]


def build_package_manifest() -> dict[str, object]:
    return {
        "phase": "V8C_QUANT_BENCHMARK_ESP32_PACKAGE",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline": "MLP V7C/V8B2 float",
        "candidate_role": "experimental quantized or compact candidate",
        "target": "Method B / soc_q_cycle",
        "feature_order": FEATURE_ORDER,
        "current_unit": "mA",
        "scaler_policy": "sklearn.MinMaxScaler-compatible; do not clip scaled features",
        "clipping_policy": "clip only final SOC to [0, 1]",
        "replay_files": REPLAY_FILES,
        "log_return_fields": LOG_FIELDS,
        "log_collection_criteria": [
            "Run GOLDEN, EXTENDED, and ANOMALY with baseline float and candidate when available.",
            "Preserve sample_id and mode from replay vectors.",
            "Record inference_time_ms for each sample.",
            "Record free_heap and min_free_heap when available.",
            "Record flash_bytes or binary size when available.",
            "Do not report field, production, 24/7, physical sensor, or operational SOH claims.",
        ],
    }


def write_manifest(path: Path, manifest: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_return_template(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(LOG_FIELDS)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate ESP32 return manifest and CSV template for V8C benchmark.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--template", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest_path = args.manifest or args.output_dir / "v8c_esp32_benchmark_package_manifest.json"
    template_path = args.template or DEFAULT_TEMPLATE
    write_manifest(manifest_path, build_package_manifest())
    write_return_template(template_path)
    print(f"ESP32 package manifest: {manifest_path}")
    print(f"ESP32 return template: {template_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

