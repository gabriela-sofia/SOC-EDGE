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
BASELINE_HEADER = "embedded/handoff_v8b2/include/canonical_model_weights_v8b2.h"
CANDIDATE_HEADER = "embedded/handoff_v8c_quant_benchmark/include/candidate_quantized_model.h"
REPLAY_HEADER = "embedded/handoff_v8b2/include/replay_vectors_v8b2.h"
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
    "heap_free",
    "heap_min_free",
    "flash_bytes",
    "max_alloc_heap",
    "anomaly_flag",
    "status",
]


def build_package_manifest() -> dict[str, object]:
    return {
        "phase": "V8C_QUANT_BENCHMARK_ESP32_PACKAGE",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline": "MLP V7C/V8B2 float",
        "candidate_role": "experimental quantized or compact candidate",
        "candidate_current_offline_status": "implemented for benchmark; max_abs_diff exceeds the initial conservative limit",
        "conservative_max_abs_diff_limit": 0.01,
        "baseline_header": BASELINE_HEADER,
        "candidate_header": CANDIDATE_HEADER,
        "replay_vectors_header": REPLAY_HEADER,
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
            "Record heap_free, heap_min_free, and max_alloc_heap when available.",
            "Record flash_bytes or binary size when available.",
            "Return one log set for model_variant=baseline_float and one for model_variant=v8c_int8_candidate.",
            "Do not report field, production, 24/7, physical sensor, or operational SOH claims.",
        ],
        "operator_instructions": [
            f"Compile the baseline firmware with {BASELINE_HEADER}.",
            f"Compile an experimental candidate variant including {CANDIDATE_HEADER}.",
            f"Use replay vectors from {REPLAY_HEADER} and the CSV replay files listed here.",
            "Run GOLDEN, EXTENDED, and ANOMALY modes for each model variant.",
            "Return the completed CSV template and raw serial logs; no Python knowledge is required.",
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
