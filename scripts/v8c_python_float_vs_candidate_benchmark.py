from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path

try:
    from compare_v8b2_float_vs_dequantized import (
        FEATURE_COLUMNS,
        build_model,
        load_header,
        predict,
        read_replay_csv,
    )
except ModuleNotFoundError:
    from scripts.compare_v8b2_float_vs_dequantized import (
        FEATURE_COLUMNS,
        build_model,
        load_header,
        predict,
        read_replay_csv,
    )


DEFAULT_BASELINE_HEADER = Path("embedded/handoff_v8b2/include/canonical_model_weights_v8b2.h")
DEFAULT_CANDIDATE_HEADER = Path("embedded/handoff_v8c_quant_benchmark/include/candidate_quantized_model.h")
DEFAULT_REPLAY_CSVS = [
    Path("embedded/handoff_v8b2/replay/canonical_golden_vectors_v8b2.csv"),
    Path("embedded/handoff_v8b2/replay/canonical_extended_replay_v8b2.csv"),
]
DEFAULT_OUTPUT_DIR = Path("reports/v8c_quant_benchmark")


def finite(value: float) -> bool:
    return math.isfinite(value)


def metric_summary(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"n": 0, "mae": None, "rmse": None, "max_abs_diff": None}
    return {
        "n": len(values),
        "mae": statistics.fmean(abs(value) for value in values),
        "rmse": math.sqrt(statistics.fmean(value * value for value in values)),
        "max_abs_diff": max(abs(value) for value in values),
    }


def load_rows(replay_paths: list[Path]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in replay_paths:
        rows.extend(read_replay_csv(path))
    return rows


def baseline_records(baseline_header: Path, replay_paths: list[Path]) -> tuple[list[dict[str, object]], dict[str, object]]:
    model = build_model(load_header(baseline_header), dequantized=False)
    rows = load_rows(replay_paths)
    records: list[dict[str, object]] = []
    baseline_errors: list[float] = []
    for row in rows:
        soc = predict(model, row["features"])
        reference = row["soc_reference"]
        error = None if reference is None else soc - float(reference)
        if error is not None:
            baseline_errors.append(error)
        records.append(
            {
                "sample_id": row["sample_id"],
                "mode": row["mode"],
                "source_file": row["source_file"],
                "soc_float_baseline": soc,
                "soc_candidate": None,
                "candidate_minus_float": None,
                "soc_reference": reference,
                "float_error_vs_reference": error,
                "candidate_error_vs_reference": None,
                "status": "BASELINE_ONLY",
            }
        )
    summary = {
        "baseline_header": baseline_header.as_posix(),
        "feature_order": FEATURE_COLUMNS,
        "baseline_status": "BASELINE_REPORT_GENERATED",
        "baseline_error_vs_reference": metric_summary(baseline_errors),
        "n_records": len(records),
        "soc_final_clip_policy": "clip only final SOC to [0, 1]",
        "scaled_feature_clip_policy": "do not clip scaled features",
        "all_outputs_finite": all(finite(float(record["soc_float_baseline"])) for record in records),
        "all_soc_in_unit_interval": all(0.0 <= float(record["soc_float_baseline"]) <= 1.0 for record in records),
    }
    return records, summary


def compare_candidate(
    baseline_header: Path,
    candidate_header: Path,
    replay_paths: list[Path],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    records, summary = baseline_records(baseline_header, replay_paths)
    if not candidate_header.exists():
        summary.update(
            {
                "candidate_header": candidate_header.as_posix(),
                "candidate_status": "CANDIDATE_NOT_AVAILABLE",
                "candidate_error_vs_reference": metric_summary([]),
                "candidate_diff_vs_float": metric_summary([]),
            }
        )
        return records, summary

    candidate_model = build_model(load_header(candidate_header), dequantized=False)
    rows = load_rows(replay_paths)
    diffs: list[float] = []
    candidate_errors: list[float] = []
    for record, row in zip(records, rows):
        candidate_soc = predict(candidate_model, row["features"])
        diff = candidate_soc - float(record["soc_float_baseline"])
        candidate_error = None if row["soc_reference"] is None else candidate_soc - float(row["soc_reference"])
        diffs.append(diff)
        if candidate_error is not None:
            candidate_errors.append(candidate_error)
        record["soc_candidate"] = candidate_soc
        record["candidate_minus_float"] = diff
        record["candidate_error_vs_reference"] = candidate_error
        record["status"] = "CANDIDATE_COMPARED"

    summary.update(
        {
            "candidate_header": candidate_header.as_posix(),
            "candidate_status": "CANDIDATE_COMPARED",
            "candidate_error_vs_reference": metric_summary(candidate_errors),
            "candidate_diff_vs_float": metric_summary(diffs),
            "all_outputs_finite": all(
                finite(float(record["soc_float_baseline"]))
                and (record["soc_candidate"] is None or finite(float(record["soc_candidate"])))
                for record in records
            ),
            "all_soc_in_unit_interval": all(
                0.0 <= float(record["soc_float_baseline"]) <= 1.0
                and (record["soc_candidate"] is None or 0.0 <= float(record["soc_candidate"]) <= 1.0)
                for record in records
            ),
        }
    )
    return records, summary


def write_records_csv(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "sample_id",
        "mode",
        "source_file",
        "soc_float_baseline",
        "soc_candidate",
        "candidate_minus_float",
        "soc_reference",
        "float_error_vs_reference",
        "candidate_error_vs_reference",
        "status",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def write_json(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare V8C baseline float with an optional candidate model.")
    parser.add_argument("--baseline-header", type=Path, default=DEFAULT_BASELINE_HEADER)
    parser.add_argument("--candidate-header", type=Path, default=DEFAULT_CANDIDATE_HEADER)
    parser.add_argument("--replay-csv", type=Path, action="append")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--csv", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    replay_paths = args.replay_csv or DEFAULT_REPLAY_CSVS
    records, summary = compare_candidate(args.baseline_header, args.candidate_header, replay_paths)
    csv_path = args.csv or args.output_dir / "v8c_python_float_vs_candidate_predictions.csv"
    json_path = args.json or args.output_dir / "v8c_python_float_vs_candidate_summary.json"
    write_records_csv(csv_path, records)
    write_json(json_path, summary)
    print(f"candidate_status: {summary['candidate_status']}")
    print(f"records_csv: {csv_path}")
    print(f"summary_json: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

